"""
LangChain RAG chain — Grok LLM + HuggingFace local embeddings.

Robustness features:
  #1 Retry logic         — exponential backoff on Grok API failures (tenacity)
  #2 "I don't know"      — detects when retrieved docs are irrelevant
  #3 Multi-query         — rewrites query 3 ways, merges retrieved results
  #4 Page-number cites   — includes page numbers in source citations
  (#3 feedback is handled in app.py / db.py)
"""
import time
from typing import Any

from config import (
    ALLOW_DANGEROUS_DESERIALIZATION,
    CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    CIRCUIT_BREAKER_FAILURES,
    EMBEDDING_MODEL,
    ENABLE_HYBRID_SEARCH,
    ENABLE_RERANKER,
    ENABLE_VERIFICATION_PASS,
    FAISS_INDEX_DIR,
    GROK_API_KEY,
    GROK_BASE_URL,
    GROK_MODEL,
    HYBRID_BM25_WEIGHT,
    MEMORY_WINDOW,
    REQUIRE_CITATIONS,
    RETRIEVER_K,
    SYSTEM_PROMPT_PATH,
)
from ingest import index_exists
from utils.logger import get_logger
from utils.preprocessor import preprocess_query

log = get_logger(__name__)

# Minimum relevance: if ALL retrieved chunks have fewer than this many
# characters, we treat the answer as "no relevant docs found"
MIN_CONTEXT_CHARS = 100

# Retry config
MAX_RETRIES   = 3
RETRY_BACKOFF = 2   # seconds (doubles each attempt)

# Circuit breaker state (module-level, process-wide)
_cb_failures = 0
_cb_open_until = 0.0

# Error strings that signal a non-retryable failure (billing / auth)
_NO_RETRY_PHRASES = [
    "credits or licenses",   # 403 — no billing credits
    "Incorrect API key",     # 400 — wrong key format
    "invalid_api_key",       # OpenAI-style error code
    "No API key",
]


# ── Embeddings ────────────────────────────────────────────────────────────────

def _get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ── Prompt ────────────────────────────────────────────────────────────────────

def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return "You are a helpful PayGlobal AI assistant. Use the context below:\n{context}"


def build_qa_prompt():
    from langchain_core.prompts import PromptTemplate
    system   = _load_system_prompt()
    template = system + "\n\nQuestion: {question}\n\nAnswer:"
    return PromptTemplate(input_variables=["context", "question"], template=template)


# ── #3 Multi-query retrieval ─────────────────────────────────────────────────

def _multi_query_retrieve(vectorstore, question: str, llm, k: int = RETRIEVER_K) -> list:
    """
    Rewrite the question 3 different ways, retrieve from each,
    deduplicate by page_content hash, return merged unique docs.
    """
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate

    rewrite_prompt = PromptTemplate(
        input_variables=["question"],
        template=(
            "Generate 3 different versions of the following question to improve "
            "document retrieval. Return ONLY the 3 questions, one per line.\n\n"
            "Original question: {question}\n\n3 versions:"
        ),
    )

    try:
        chain  = rewrite_prompt | llm | StrOutputParser()
        output = chain.invoke({"question": question})
        variants = [q.strip() for q in output.strip().split("\n") if q.strip()][:3]
    except Exception as e:
        log.warning(f"Multi-query rewrite failed, falling back to single query: {e}")
        variants = [question]

    # Always include the original
    all_queries = list(dict.fromkeys([question] + variants))

    # Retrieve from each query and deduplicate
    seen    = set()
    results = []
    for q in all_queries:
        try:
            docs = vectorstore.similarity_search(q, k=k)
            for d in docs:
                key = hash(d.page_content[:200])
                if key not in seen:
                    seen.add(key)
                    results.append(d)
        except Exception as e:
            log.warning(f"Retrieval failed for variant '{q[:40]}': {e}")

    log.info(f"Multi-query: {len(all_queries)} queries -> {len(results)} unique chunks")
    return results[:k * 2]   # cap total


def _build_bm25(vectorstore) -> tuple[list, Any] | tuple[None, None]:
    """
    Build a BM25 index over the FAISS docstore texts.
    Cached on the chain instance.
    """
    try:
        from rank_bm25 import BM25Okapi

        docs = list(vectorstore.docstore._dict.values())
        corpus_tokens = [(d.page_content or "").lower().split() for d in docs]
        bm25 = BM25Okapi(corpus_tokens)
        return docs, bm25
    except Exception:
        return None, None


def _bm25_search(chain, query: str, top_k: int) -> list:
    vs = getattr(chain, "_vectorstore", None)
    if not vs:
        return []
    if getattr(chain, "_bm25", None) is None or getattr(chain, "_bm25_docs", None) is None:
        docs, bm25 = _build_bm25(vs)
        chain._bm25_docs = docs
        chain._bm25 = bm25
    bm25 = getattr(chain, "_bm25", None)
    docs = getattr(chain, "_bm25_docs", None)
    if not bm25 or not docs:
        return []
    try:
        scores = bm25.get_scores(query.lower().split())
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [docs[i] for i in idxs if scores[i] > 0]
    except Exception:
        return []


def _apply_metadata_filter(docs: list, module_filter: str | None) -> list:
    if not module_filter or module_filter == "All Modules":
        return docs
    wanted = module_filter.strip().lower()
    out = []
    for d in docs:
        m = (d.metadata or {}).get("module") or ""
        if str(m).strip().lower() == wanted:
            out.append(d)
    return out


def _apply_extra_filters(docs: list, year: str, version: str, customer: str) -> list:
    year = (year or "").strip().lower()
    version = (version or "").strip().lower()
    customer = (customer or "").strip().lower()
    if not (year or version or customer):
        return docs
    out = []
    for d in docs:
        meta = d.metadata or {}
        y = str(meta.get("year") or "").strip().lower()
        v = str(meta.get("version") or "").strip().lower()
        c = str(meta.get("customer") or "").strip().lower()
        if year and year not in y:
            continue
        if version and version not in v:
            continue
        if customer and customer not in c:
            continue
        out.append(d)
    return out


def _rrf_fuse(vec_docs: list, bm_docs: list, weight_bm25: float, k: int = 60) -> tuple[list, dict]:
    """
    Weighted Reciprocal Rank Fusion.
    score(doc) = (1-w)*1/(k+rank_vec) + w*1/(k+rank_bm25)
    """
    w = min(1.0, max(0.0, float(weight_bm25)))
    scores: dict[int, float] = {}
    seen_docs: dict[int, Any] = {}

    def _add(docs: list, base_weight: float):
        for idx, d in enumerate(docs):
            key = hash((d.page_content or "")[:300])
            seen_docs[key] = d
            scores[key] = scores.get(key, 0.0) + base_weight * (1.0 / (k + idx + 1))

    _add(vec_docs, 1.0 - w)
    _add(bm_docs, w)

    merged = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    fused = [seen_docs[key] for key, _ in merged]
    stats = {
        "vec": len(vec_docs),
        "bm25": len(bm_docs),
        "fused": len(fused),
        "weight_bm25": w,
    }
    return fused, stats


def _log_retrieval(docs: list, label: str) -> None:
    try:
        top = []
        for d in docs[: min(8, len(docs))]:
            meta = d.metadata or {}
            top.append(
                {
                    "file": meta.get("source_file", "Unknown"),
                    "page": meta.get("page"),
                    "module": meta.get("module", ""),
                    "section": meta.get("section", ""),
                    "chars": len(d.page_content or ""),
                }
            )
        log.info(f"{label}: retrieved={len(docs)} top={top}")
    except Exception:
        pass


def _verification_pass(llm, question: str, answer: str, sources: list[dict]) -> str:
    """
    Optional post-check to reduce hallucinations:
    - ensure the answer is consistent with sources
    - ensure citations exist if required
    """
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        prompt = PromptTemplate(
            input_variables=["question", "answer", "sources"],
            template=(
                "You are a strict enterprise QA reviewer.\n"
                "Check the assistant answer for correctness and grounding.\n\n"
                "Question:\n{question}\n\n"
                "Answer:\n{answer}\n\n"
                "Sources (file/page pairs):\n{sources}\n\n"
                "Rules:\n"
                "- If the answer makes a claim not supported by sources, rewrite the answer to be conservative.\n"
                "- Keep it concise and professional.\n"
                "- If sources are empty, respond with: I don't have enough information in the loaded PayGlobal documentation to answer this accurately.\n\n"
                "Revised answer:"
            ),
        )
        chain = prompt | llm | StrOutputParser()
        revised = chain.invoke({"question": question, "answer": answer, "sources": str(sources)[:1500]})
        return (revised or "").strip() or answer
    except Exception:
        return answer


# ── #2 "I don't know" detection ──────────────────────────────────────────────

def _has_relevant_context(docs: list) -> bool:
    """Return False if retrieved docs have almost no usable content."""
    total_chars = sum(len(d.page_content) for d in docs)
    return total_chars >= MIN_CONTEXT_CHARS and len(docs) > 0


_IDK_RESPONSE = (
    "I don't have enough information in the loaded PayGlobal documentation "
    "to answer this question accurately.\n\n"
    "**Suggestions:**\n"
    "- Try rephrasing your question with different keywords\n"
    "- Check if the relevant manual has been uploaded and ingested\n"
    "- For this specific topic, please refer directly to the PayGlobal documentation"
)


# ── #4 Page-number citations ──────────────────────────────────────────────────

def _extract_sources(docs: list) -> list[dict]:
    """
    Return list of {file, page} dicts from retrieved source documents.
    Deduplicates by (file, page) pair.
    """
    seen    = set()
    sources = []
    for d in docs:
        meta = d.metadata
        file = meta.get("source_file", "Unknown")
        page = meta.get("page")                        # PyPDFLoader sets this (0-indexed)
        page_display = f"p.{page + 1}" if isinstance(page, int) else None
        key  = (file, page_display)
        if key not in seen:
            seen.add(key)
            sources.append({"file": file, "page": page_display})
    return sources


# ── #6 Re-ranking (cross-encoder) ─────────────────────────────────────────────

# Cached model instance — loaded once, reused for all queries
_reranker_model = None

def _rerank_docs(question: str, docs: list, top_k: int = RETRIEVER_K) -> list:
    """
    Cross-encoder re-ranking: score every (question, chunk) pair
    and return the top_k highest-scoring documents.
    Uses cross-encoder/ms-marco-MiniLM-L-6-v2 (fast, ~65MB, already on disk).
    Falls back to original order if anything fails.
    """
    global _reranker_model
    if not docs:
        return docs
    if not ENABLE_RERANKER:
        return docs[:top_k]
    try:
        from sentence_transformers import CrossEncoder
        if _reranker_model is None:
            _reranker_model = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                max_length=512,
            )
        pairs  = [(question, d.page_content[:400]) for d in docs]
        scores = _reranker_model.predict(pairs)
        ranked = sorted(zip(scores, docs, strict=False), key=lambda x: x[0], reverse=True)
        result = [d for _, d in ranked[:top_k]]
        log.info(f"Re-ranker: {len(docs)} chunks -> kept top {len(result)}")
        return result
    except Exception as e:
        log.warning(f"Re-ranking skipped: {e}")
        return docs[:top_k]


# ── Chain builder ─────────────────────────────────────────────────────────────

def get_rag_chain(
    api_key: str = None,
    model: str = None,
    chat_history: list[tuple[str, str]] = None,
):
    from langchain_classic.chains import ConversationalRetrievalChain
    from langchain_classic.memory import ConversationBufferWindowMemory
    from langchain_community.vectorstores import FAISS
    from langchain_openai import ChatOpenAI

    key = api_key or GROK_API_KEY
    mdl = model   or GROK_MODEL

    if not key:
        raise ValueError("Grok API key not set. Add GROK_API_KEY to .env or enter it in the sidebar.")
    if not index_exists():
        raise FileNotFoundError("No FAISS index found. Upload and ingest documents first.")

    embeddings  = _get_embeddings()
    vectorstore = FAISS.load_local(
        str(FAISS_INDEX_DIR), embeddings,
        allow_dangerous_deserialization=ALLOW_DANGEROUS_DESERIALIZATION,
    )
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": RETRIEVER_K},
    )
    llm = ChatOpenAI(model=mdl, temperature=0.1, api_key=key, base_url=GROK_BASE_URL)

    memory = ConversationBufferWindowMemory(
        k=MEMORY_WINDOW,
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
    )
    if chat_history:
        for human_msg, ai_msg in chat_history[-MEMORY_WINDOW:]:
            memory.chat_memory.add_user_message(human_msg)
            memory.chat_memory.add_ai_message(ai_msg)

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        verbose=False,
        combine_docs_chain_kwargs={"prompt": build_qa_prompt()},
    )

    # Attach vectorstore + llm for multi-query access
    chain._vectorstore = vectorstore
    chain._llm         = llm
    chain._bm25_docs = None
    chain._bm25 = None

    log.info(f"RAG chain ready — {mdl} @ {GROK_BASE_URL}")
    return chain


# ── #1 Ask with retry + #2 IDK + #3 multi-query + #4 page cites ─────────────

def ask(chain, question: str) -> dict[str, Any]:
    """
    Ask a question with:
      - Multi-query retrieval (#3)
      - "I don't know" detection (#2)
      - Exponential backoff retry (#1)
      - Page-number citations (#4)

    Returns:
      {
        "answer":  str,
        "sources": [{"file": str, "page": str|None}, ...],
        "retries": int,
      }
    """
    global _cb_failures, _cb_open_until
    now_ts = time.time()
    if _cb_open_until and now_ts < _cb_open_until:
        return {
            "answer": "⚠️ The AI service is temporarily unavailable. Please try again in a minute.",
            "sources": [],
            "retries": 0,
            "idk": False,
            "error_type": "circuit_open",
        }

    # ── #7 Query preprocessing ────────────────────────────────────────────
    processed_question = preprocess_query(question)
    if processed_question != question:
        log.info(f"Query expanded: '{question}' -> '{processed_question}'")

    # ── #3 Multi-query retrieval ──────────────────────────────────────────
    vs  = getattr(chain, "_vectorstore", None)
    llm = getattr(chain, "_llm", None)

    t0 = time.time()
    if vs and llm:
        vec_docs = _multi_query_retrieve(vs, processed_question, llm)
    else:
        vec_docs = chain.retriever.get_relevant_documents(processed_question)

    bm_docs = _bm25_search(chain, processed_question, RETRIEVER_K * 2) if (ENABLE_HYBRID_SEARCH and llm) else []
    fused, hybrid_stats = _rrf_fuse(vec_docs, bm_docs, HYBRID_BM25_WEIGHT)

    # Optional module filter (based on Streamlit module selection)
    module_filter = None
    filter_year = ""
    filter_version = ""
    filter_customer = ""
    try:
        import streamlit as st

        module_filter = st.session_state.get("module")
        filter_year = st.session_state.get("filter_year", "")
        filter_version = st.session_state.get("filter_version", "")
        filter_customer = st.session_state.get("filter_customer", "")
    except Exception:
        module_filter = None
    src_docs = _apply_metadata_filter(fused, module_filter)
    src_docs = _apply_extra_filters(src_docs, filter_year, filter_version, filter_customer)

    retrieval_ms = int((time.time() - t0) * 1000)
    log.info(f"Hybrid stats: {hybrid_stats} retrieval_ms={retrieval_ms}")
    _log_retrieval(src_docs, "Retrieval")

    # ── #6 Re-ranking ─────────────────────────────────────────────────────
    src_docs = _rerank_docs(processed_question, src_docs)

    # ── #2 "I don't know" detection ───────────────────────────────────────
    if not _has_relevant_context(src_docs):
        log.info("No relevant context found — returning IDK response")
        return {
            "answer":  _IDK_RESPONSE,
            "sources": [],
            "retries": 0,
            "idk":     True,
        }

    # ── #1 Retry with exponential backoff ─────────────────────────────────
    error_type  = "api_error"   # default; may be overridden below

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result   = chain({"question": question})
            answer   = result.get("answer", "")
            raw_docs = result.get("source_documents", src_docs)

            # ── #4 Page-number citations ──────────────────────────────────
            sources = _extract_sources(raw_docs)
            if REQUIRE_CITATIONS and not sources:
                return {
                    "answer": _IDK_RESPONSE,
                    "sources": [],
                    "retries": attempt - 1,
                    "idk": True,
                    "error_type": None,
                }

            if ENABLE_VERIFICATION_PASS and llm:
                answer = _verification_pass(llm, question, answer, sources)

            _cb_failures = 0
            return {
                "answer":     answer,
                "sources":    sources,
                "retries":    attempt - 1,
                "idk":        False,
                "error_type": None,
            }

        except Exception as e:
            _cb_failures += 1
            if _cb_failures >= CIRCUIT_BREAKER_FAILURES:
                _cb_open_until = time.time() + float(CIRCUIT_BREAKER_COOLDOWN_SECONDS)
            err_str     = str(e)

            # ── Detect non-retryable errors ───────────────────────────────
            if "credits or licenses" in err_str:
                error_type = "no_credits"
                log.error(f"Billing error — no xAI credits: {e}")
                break   # no point retrying

            if any(p in err_str for p in ["Incorrect API key", "invalid_api_key", "No API key"]):
                error_type = "invalid_key"
                log.error(f"Invalid Grok API key: {e}")
                break   # no point retrying

            # ── Transient errors → retry with backoff ─────────────────────
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                log.warning(f"Grok API error (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                log.error(f"All {MAX_RETRIES} attempts failed: {e}")

    # ── Build user-visible error answer ───────────────────────────────────
    if error_type == "no_credits":
        answer_msg = (
            "⚠️ **No API Credits / Quota Exceeded**\n\n"
            "Your API quota has been exhausted. If you're using the **free Groq tier**, "
            "get a fresh key at [console.groq.com](https://console.groq.com) "
            "and paste it in the sidebar under **🔑 API Key**."
        )
    elif error_type == "invalid_key":
        answer_msg = (
            "🔑 **Invalid API Key**\n\n"
            "The Grok API key provided doesn't appear to be valid. "
            "Please update it in the sidebar under **🔑 Grok API Key**."
        )
    else:
        answer_msg = (
            f"The AI service is temporarily unavailable after {MAX_RETRIES} attempts.\n\n"
            "Please try again in a moment."
        )

    return {
        "answer":     answer_msg,
        "sources":    [],
        "retries":    MAX_RETRIES,
        "idk":        False,
        "error_type": error_type,
    }
