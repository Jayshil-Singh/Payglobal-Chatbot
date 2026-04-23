"""
PayGlobal AI Assistant — Streamlit Application
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

# ── Page config MUST be first ──────────────────────────────────────────────
st.set_page_config(
    page_title="PayGlobal AI Assistant",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ────────────────────────────────────────────────────────────────
from config import PAYGLOBAL_MODULES, APP_TITLE, GROK_API_KEY, UPLOADS_DIR
from auth import bootstrap_admin, login, register
from db import (
    create_conversation, get_user_conversations, get_messages,
    save_message, delete_conversation, update_conversation_title,
    save_feedback,
)
from ingest import ingest_file, index_exists
from rag_chain import get_rag_chain, ask

# Bootstrap DB + admin account on every cold start
bootstrap_admin()

# ══════════════════════════════════════════════════════════════════════════
# CUSTOM CSS — dark premium theme
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #070b14; color: #e6edf3; }

/* ── Hide default chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 100%; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid rgba(48,54,61,0.8);
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #4f6ef7;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 1rem 0 0.4rem 0;
}

/* ── Sidebar buttons ── */
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    color: #8b949e;
    border: 1px solid rgba(48,54,61,0.6);
    border-radius: 8px;
    font-size: 0.82rem;
    padding: 0.45rem 0.8rem;
    text-align: left;
    transition: all 0.2s ease;
    margin-bottom: 3px;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(79,110,247,0.12);
    color: #e6edf3;
    border-color: rgba(79,110,247,0.4);
}

/* ── Selectbox ── */
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #161b27 !important;
    border: 1px solid rgba(48,54,61,0.8) !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #0d1117;
    border: 1px solid rgba(48,54,61,0.6);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: #161b27 !important;
    border: 1px solid rgba(79,110,247,0.3) !important;
    border-radius: 12px !important;
    color: #e6edf3 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(79,110,247,0.8) !important;
    box-shadow: 0 0 0 2px rgba(79,110,247,0.15) !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f6ef7, #7c3aed);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.25s ease;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(79,110,247,0.35);
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #161b27 !important;
    border-radius: 8px !important;
    color: #8b949e !important;
    font-size: 0.8rem !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stTextInput > div > div > input:focus {
    background: #161b27 !important;
    border: 1px solid rgba(48,54,61,0.8) !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
}

/* ── Alerts / info ── */
.stAlert { border-radius: 10px; }

/* ── Logo card ── */
.logo-card {
    background: linear-gradient(135deg, rgba(79,110,247,0.15), rgba(124,58,237,0.1));
    border: 1px solid rgba(79,110,247,0.25);
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
    margin-bottom: 1rem;
}
.logo-card h2 { color: #e6edf3; margin: 0; font-size: 1rem; font-weight: 700; }
.logo-card p  { color: #8b949e; margin: 0.2rem 0 0 0; font-size: 0.75rem; }

/* ── Login card ── */
.login-card {
    background: #0d1117;
    border: 1px solid rgba(48,54,61,0.8);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    max-width: 420px;
    margin: 0 auto;
}
.login-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6edf3;
    text-align: center;
    margin-bottom: 0.3rem;
}
.login-sub {
    color: #8b949e;
    text-align: center;
    font-size: 0.85rem;
    margin-bottom: 2rem;
}

/* ── Conversation item ── */
.conv-item {
    padding: 0.5rem 0.7rem;
    border-radius: 8px;
    font-size: 0.82rem;
    color: #8b949e;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.2s;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.conv-item:hover, .conv-item.active {
    background: rgba(79,110,247,0.12);
    color: #e6edf3;
    border-color: rgba(79,110,247,0.3);
}

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
}
.badge-blue  { background: rgba(79,110,247,0.2);  color: #4f6ef7; }
.badge-green { background: rgba(16,185,129,0.2);  color: #10b981; }
.badge-red   { background: rgba(239,68,68,0.2);   color: #ef4444; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #161b27;
    border: 2px dashed rgba(79,110,247,0.3);
    border-radius: 12px;
    padding: 0.5rem;
}

/* ── Top header bar ── */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 1rem 0;
    border-bottom: 1px solid rgba(48,54,61,0.6);
    margin-bottom: 1rem;
}
.topbar-title { font-size: 1.1rem; font-weight: 700; color: #e6edf3; }
.topbar-user  { font-size: 0.8rem; color: #8b949e; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "authenticated": False,
        "user":          None,
        "conv_id":       None,
        "messages":      [],   # [{role, content, sources}]
        "rag_chain":     None,
        "module":        "All Modules",
        "show_login":    True,  # False = show register
        "api_key":       GROK_API_KEY,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════
def load_chain():
    """(Re)build the RAG chain, pulling history from current conversation."""
    history = []
    if st.session_state.conv_id:
        msgs = get_messages(st.session_state.conv_id)
        pairs = []
        buf = {}
        for m in msgs:
            if m["role"] == "user":
                buf = {"q": m["content"]}
            elif m["role"] == "assistant" and buf:
                pairs.append((buf["q"], m["content"]))
                buf = {}
        history = pairs

    st.session_state.rag_chain = get_rag_chain(
        api_key=st.session_state.api_key,
        chat_history=history,
    )


def start_new_conversation():
    user_id = st.session_state.user["id"]
    conv_id = create_conversation(user_id, "New Chat", st.session_state.module)
    st.session_state.conv_id  = conv_id
    st.session_state.messages = []
    st.session_state.rag_chain = None


def load_conversation(conv_id: int):
    st.session_state.conv_id = conv_id
    msgs = get_messages(conv_id)
    st.session_state.messages = [
        {
            "role":    m["role"],
            "content": m["content"],
            "sources": m["sources"],
            "msg_id":  m["id"],     # restore DB id so feedback buttons work
        }
        for m in msgs
    ]
    st.session_state.rag_chain = None   # will be rebuilt on next ask



def auto_title(conv_id: int, first_user_msg: str):
    """Set conversation title from first user message."""
    title = first_user_msg[:55] + ("…" if len(first_user_msg) > 55 else "")
    update_conversation_title(conv_id, title)


# ══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════
def show_login_page():
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("""
        <div style='text-align:center; margin-top:3rem; margin-bottom:2rem;'>
            <div style='font-size:3.5rem;'>🌐</div>
            <h1 style='color:#e6edf3; font-size:1.9rem; font-weight:700; margin:0.3rem 0;'>
                PayGlobal AI Assistant
            </h1>
            <p style='color:#8b949e; font-size:0.9rem;'>
                Your intelligent PayGlobal implementation expert
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 Sign In", "✏️ Register"])

        # ── Login tab ──
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = login(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.api_key = GROK_API_KEY
                        st.success(f"Welcome back, {user['username']}! 👋")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            st.markdown("""
            <div style='background:rgba(79,110,247,0.08); border:1px solid rgba(79,110,247,0.2);
                         border-radius:8px; padding:0.7rem 1rem; margin-top:1rem; font-size:0.8rem; color:#8b949e;'>
                🔑 Default credentials: <code style='color:#4f6ef7;'>admin</code> / <code style='color:#4f6ef7;'>PayGlobal@2024</code>
            </div>
            """, unsafe_allow_html=True)

        # ── Register tab ──
        with tab_register:
            with st.form("reg_form"):
                new_user  = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email (optional)", placeholder="your@email.com")
                new_pass  = st.text_input("Password", type="password", placeholder="Min 8 characters")
                new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
                reg_btn   = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if reg_btn:
                if new_pass != new_pass2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user = register(new_user, new_pass, new_email)
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Account created! Welcome aboard 🎉")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
def show_sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div class='logo-card'>
            <div style='font-size:2rem;'>🌐</div>
            <h2>PayGlobal AI</h2>
            <p>Implementation Expert</p>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.user
        st.markdown(f"""
        <div style='text-align:center; margin-bottom:0.8rem;'>
            <span style='font-size:0.8rem; color:#8b949e;'>
                👤 {user['username']}
                <span class='badge badge-{"blue" if user["role"]=="admin" else "green"}'>{user['role']}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

        # New Chat
        if st.button("➕  New Chat", use_container_width=True):
            start_new_conversation()
            st.rerun()

        st.divider()

        # Module selector
        st.markdown("### 📦 Module Filter")
        module = st.selectbox(
            "Module", PAYGLOBAL_MODULES,
            index=PAYGLOBAL_MODULES.index(st.session_state.module),
            label_visibility="collapsed",
        )
        if module != st.session_state.module:
            st.session_state.module = module

        # Grok API Key
        st.markdown("### 🔑 Grok API Key")
        api_key_input = st.text_input(
            "Grok API Key",
            value=st.session_state.api_key,
            type="password",
            label_visibility="collapsed",
            placeholder="gsk_...",
        )
        if api_key_input != st.session_state.api_key:
            st.session_state.api_key   = api_key_input
            st.session_state.rag_chain = None   # force rebuild

        st.divider()

        # Conversation history
        st.markdown("### 💬 Conversations")
        convs = get_user_conversations(user["id"])
        if not convs:
            st.caption("No conversations yet.")
        for conv in convs:
            c1, c2 = st.columns([5, 1])
            with c1:
                label = conv["title"] or "New Chat"
                active = conv["id"] == st.session_state.conv_id
                btn_style = "primary" if active else "secondary"
                if st.button(f"{'▶ ' if active else ''}{label}", key=f"conv_{conv['id']}", use_container_width=True):
                    load_conversation(conv["id"])
                    st.rerun()
            with c2:
                if st.button("🗑", key=f"del_{conv['id']}"):
                    delete_conversation(conv["id"])
                    if st.session_state.conv_id == conv["id"]:
                        st.session_state.conv_id  = None
                        st.session_state.messages  = []
                        st.session_state.rag_chain = None
                    st.rerun()

        st.divider()

        # Document upload
        st.markdown("### 📄 Upload Documents")
        uploaded_files = st.file_uploader(
            "Drop PDFs or DOCX here",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files:
            if st.button("⚡ Ingest Documents", use_container_width=True, type="primary"):
                if not st.session_state.api_key:
                    st.error("Please enter your Grok API key first.")
                else:
                    total_chunks = 0
                    with st.spinner("Ingesting documents…"):
                        for uf in uploaded_files:
                            save_path = UPLOADS_DIR / uf.name
                            save_path.write_bytes(uf.getbuffer())
                            try:
                                n = ingest_file(save_path)
                                total_chunks += n
                            except Exception as e:
                                st.error(f"Error ingesting {uf.name}: {e}")
                    st.success(f"✅ {len(uploaded_files)} file(s) ingested → {total_chunks} chunks added.")
                    st.session_state.rag_chain = None   # force rebuild with new docs

        st.divider()

        # ── Export Conversation (#8) ──────────────────────────────────────
        st.markdown("### 💾 Export Conversation")
        messages = st.session_state.get("messages", [])
        if not messages:
            st.caption("No messages to export yet.")
        else:
            # Build markdown export
            lines = [
                f"# PayGlobal AI Assistant — Conversation Export",
                f"**User:** {st.session_state.user['username']}",
                f"**Module:** {st.session_state.module}",
                f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "---",
                "",
            ]
            for msg in messages:
                role_label = "🧑 **You**" if msg["role"] == "user" else "🤖 **PayGlobal AI**"
                lines.append(f"{role_label}")
                lines.append("")
                lines.append(msg["content"])
                sources = msg.get("sources", [])
                if sources and msg["role"] == "assistant":
                    lines.append("")
                    lines.append("*Sources:*")
                    for src in sources:
                        if isinstance(src, dict):
                            file = src.get("file", "")
                            page = src.get("page", "")
                            lines.append(f"- `{file}`" + (f" — {page}" if page else ""))
                        else:
                            lines.append(f"- `{src}`")
                lines.append("")
                lines.append("---")
                lines.append("")

            export_text = "\n".join(lines)
            filename = f"payglobal_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            st.download_button(
                label="⬇️ Download as Markdown",
                data=export_text.encode("utf-8"),
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
            )

        st.divider()

        # Logout
        if st.button("🚪  Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()



# ══════════════════════════════════════════════════════════════════════════
# MAIN CHAT INTERFACE
# ══════════════════════════════════════════════════════════════════════════
def show_chat():
    # Top bar
    st.markdown(f"""
    <div class='topbar'>
        <span class='topbar-title'>🌐 {APP_TITLE}</span>
        <span class='topbar-user'>
            Module: <b style='color:#4f6ef7;'>{st.session_state.module}</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Ensure a conversation exists
    if not st.session_state.conv_id:
        start_new_conversation()

    # ── Render message history ──
    messages = st.session_state.messages

    if not messages:
        st.markdown("""
        <div style='text-align:center; padding:4rem 2rem; color:#8b949e;'>
            <div style='font-size:3rem; margin-bottom:1rem;'>💬</div>
            <h3 style='color:#e6edf3; margin-bottom:0.5rem;'>Ask me anything about PayGlobal</h3>
            <p style='font-size:0.9rem;'>Installation · Configuration · Troubleshooting · Functional Guidance</p>
        </div>
        """, unsafe_allow_html=True)

        # Example prompts
        example_prompts = [
            "How do I install the PayGlobal Payroll module?",
            "Configure ESS portal step by step",
            "Fix database connection error during setup",
            "Setup employee master data",
        ]
        cols = st.columns(2)
        for i, prompt in enumerate(example_prompts):
            with cols[i % 2]:
                if st.button(f"💡 {prompt}", use_container_width=True, key=f"ex_{i}"):
                    st.session_state._pending_prompt = prompt
                    st.rerun()
    else:
        for idx, msg in enumerate(messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # ── Page-number citations (#4) ──
                if msg["role"] == "assistant" and msg.get("sources"):
                    with st.expander(f"📚 Sources ({len(msg['sources'])} reference(s))"):
                        for src in msg["sources"]:
                            if isinstance(src, dict):
                                file = src.get("file", "Unknown")
                                page = src.get("page")
                                label = f"📄 `{file}`" + (f"  —  {page}" if page else "")
                            else:
                                label = f"📄 `{src}`"
                            st.markdown(label)

                # ── Thumbs up/down feedback (#3) ──
                if msg["role"] == "assistant" and msg.get("msg_id"):
                    msg_id = msg["msg_id"]
                    col_up, col_dn, col_spacer = st.columns([1, 1, 8])
                    with col_up:
                        if st.button("👍", key=f"up_{msg_id}_{idx}", help="Good answer"):
                            save_feedback(msg_id, st.session_state.user["id"], 1)
                            st.toast("Thanks for your feedback!", icon="👍")
                    with col_dn:
                        if st.button("👎", key=f"dn_{msg_id}_{idx}", help="Bad answer"):
                            save_feedback(msg_id, st.session_state.user["id"], -1)
                            st.toast("Feedback recorded — we'll improve!", icon="👎")

    # ── Handle example prompt click ──
    pending = st.session_state.pop("_pending_prompt", None)

    # ── Chat input ──
    user_input = st.chat_input(
        "Ask about PayGlobal installation, configuration, or troubleshooting…",
    ) or pending

    if user_input:
        _handle_message(user_input)


def _handle_message(user_input: str):
    """Process a user message: save, run RAG, save response."""
    conv_id = st.session_state.conv_id

    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": user_input, "sources": []})
    save_message(conv_id, "user", user_input)

    # Auto-title on first message
    if len(st.session_state.messages) == 1:
        auto_title(conv_id, user_input)

    # Build chain if needed
    if st.session_state.rag_chain is None:
        if not st.session_state.api_key:
            st.warning("⚠️ Please enter your Grok API Key in the sidebar.")
            return
        if not index_exists():
            st.warning("⚠️ No documents indexed yet. Upload PDFs/DOCX in the sidebar and click **Ingest Documents**.")
            return
        with st.spinner("Initialising AI engine…"):
            try:
                load_chain()
            except Exception as e:
                st.error(f"Failed to load AI engine: {e}")
                return

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result  = ask(st.session_state.rag_chain, user_input)
                answer  = result["answer"]
                sources = result["sources"]     # list of {file, page} dicts
                retries = result.get("retries", 0)
                if retries > 0:
                    st.caption(f"⚠️ Needed {retries} retry attempt(s) to reach Grok API.")
            except Exception as e:
                answer  = f"⚠️ An error occurred: {e}\n\nPlease check your API key and try again."
                sources = []

        st.markdown(answer)

        # Page-number citations
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

    # Persist AI message and capture its DB id for feedback
    msg_id = save_message(conv_id, "assistant", answer, sources)
    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "sources": sources,
        "msg_id":  msg_id,
    })
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    show_login_page()
else:
    show_sidebar()
    show_chat()
