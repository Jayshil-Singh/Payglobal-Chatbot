import streamlit as st

from config import RATE_LIMIT_PER_HOUR
from db2 import (
    create_conversation,
    get_messages,
    get_request_count_last_hour,
    save_message,
    update_conversation_title,
)
from ingest import index_exists
from rag_chain import ask, get_rag_chain


def load_chain() -> None:
    """Build the RAG chain from current conversation history."""
    history = []
    if st.session_state.conv_id:
        msgs = get_messages(st.session_state.conv_id)
        pairs = []
        buffer_entry = {}
        for msg in msgs:
            if msg["role"] == "user":
                buffer_entry = {"q": msg["content"]}
            elif msg["role"] == "assistant" and buffer_entry:
                pairs.append((buffer_entry["q"], msg["content"]))
                buffer_entry = {}
        history = pairs

    st.session_state.rag_chain = get_rag_chain(
        api_key=st.session_state.api_key,
        chat_history=history,
    )


def start_new_conversation() -> None:
    # Do not persist an empty chat in DB.
    st.session_state.conv_id = None
    st.session_state.messages = []
    st.session_state.rag_chain = None


def load_conversation(conv_id: int) -> None:
    st.session_state.conv_id = conv_id
    msgs = get_messages(conv_id)
    st.session_state.messages = [
        {
            "role": msg["role"],
            "content": msg["content"],
            "sources": msg["sources"],
            "msg_id": msg["id"],
        }
        for msg in msgs
    ]
    st.session_state.rag_chain = None


def auto_title(conv_id: int, first_user_msg: str) -> None:
    title = first_user_msg[:55] + ("…" if len(first_user_msg) > 55 else "")
    update_conversation_title(conv_id, title)


def handle_message(user_input: str) -> None:
    conv_id = st.session_state.conv_id
    user = st.session_state.user

    if user["role"] != "admin":
        count = get_request_count_last_hour(user["id"])
        if count >= RATE_LIMIT_PER_HOUR:
            st.warning(
                f"⏳ Rate limit reached: you can send up to **{RATE_LIMIT_PER_HOUR} messages per hour**. "
                f"You've sent **{count}** in the last 60 minutes. Please wait before trying again."
            )
            return

    if conv_id is None:
        conv_id = create_conversation(user["id"], "New Chat", st.session_state.module)
        st.session_state.conv_id = conv_id

    st.session_state.messages.append({"role": "user", "content": user_input, "sources": []})
    save_message(conv_id, "user", user_input)

    if len(st.session_state.messages) == 1:
        auto_title(conv_id, user_input)

    if st.session_state.rag_chain is None:
        if not st.session_state.api_key:
            st.warning("⚠️ Please enter your **Groq** API Key in the sidebar.")
            return
        if not index_exists():
            st.warning("⚠️ No documents indexed yet. Upload PDFs/DOCX in the sidebar and click **Ingest Documents**.")
            return
        with st.spinner("Initialising AI engine…"):
            try:
                load_chain()
            except Exception as exc:
                err = str(exc).lower()
                if any(k in err for k in ("auth", "api key", "invalid", "incorrect", "401")):
                    st.error("🔑 Invalid Groq API key — please update it in the sidebar and try again.")
                else:
                    st.error("⚠️ Could not start the AI engine. Please check your API key in the sidebar.")
                return

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = ask(st.session_state.rag_chain, user_input)
                answer = result["answer"]
                sources = result["sources"]
                retries = result.get("retries", 0)
                if retries > 0:
                    st.caption(f"⚠️ Needed {retries} retry attempt(s) to reach Grok API.")
            except Exception as exc:
                err = str(exc).lower()
                if any(k in err for k in ("auth", "api key", "invalid", "incorrect", "401", "403")):
                    answer = (
                        "🔑 **Invalid API Key**\n\n"
                        "Your Groq API key doesn't seem to be working. "
                        "Please update it in the sidebar under **API Key** and try again.\n\n"
                        "You can get a key at [console.groq.com](https://console.groq.com/)."
                    )
                elif any(k in err for k in ("rate", "quota", "429", "too many")):
                    answer = (
                        "⏱️ **Too Many Requests**\n\n"
                        "The AI service is temporarily busy. Please wait 30 seconds and try again."
                    )
                elif any(k in err for k in ("connect", "timeout", "network", "503", "502", "unavailable")):
                    answer = (
                        "🌐 **Connection Issue**\n\n"
                        "Couldn't reach the AI service. Please check your internet connection and try again."
                    )
                elif any(k in err for k in ("index", "embed", "faiss", "no document")):
                    answer = (
                        "📄 **No Documents Indexed**\n\n"
                        "Please upload PDF or DOCX files using the sidebar and click **⚡ Ingest Documents** first."
                    )
                else:
                    answer = (
                        "⚠️ **Something went wrong**\n\n"
                        "Please try again in a moment. If the issue persists, "
                        "verify your API key is correct in the sidebar."
                    )
                sources = []

        st.markdown(answer)
        if sources:
            with st.expander(f"📚 Sources ({len(sources)} reference(s))"):
                for src in sources:
                    if isinstance(src, dict):
                        file = src.get("file", "Unknown")
                        page = src.get("page")
                        label = f"📄 `{file}`" + (f"  —  {page}" if page else "")
                    else:
                        label = f"📄 `{src}`"
                    st.markdown(label)

    msg_id = save_message(conv_id, "assistant", answer, sources)
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "msg_id": msg_id,
        }
    )
    st.rerun()
