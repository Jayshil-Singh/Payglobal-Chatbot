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
from config import PAYGLOBAL_MODULES, APP_TITLE, GROK_API_KEY, UPLOADS_DIR, RATE_LIMIT_PER_HOUR
from auth import bootstrap_admin, login, register
from db import (
    create_conversation, get_user_conversations, get_messages,
    save_message, delete_conversation, update_conversation_title,
    save_feedback, get_all_conversations_admin, get_analytics_data,
    get_all_users, get_request_count_last_hour,
)
from ingest import ingest_file, index_exists
from rag_chain import get_rag_chain, ask
from utils.exporter import export_to_pdf, export_to_docx, export_answer_pdf

# Bootstrap DB + admin account on every cold start
bootstrap_admin()

# ══════════════════════════════════════════════════════════════════════════
# CUSTOM CSS — dark premium theme
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
.stApp{background:#070b14!important;color:#e6edf3}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding:0.8rem 1.5rem 0 1.5rem!important;max-width:100%!important}

/* ── FIX THE WHITE BOTTOM INPUT BAR ── */
[data-testid="stBottom"],[data-testid="stChatInputContainer"],
.stChatInputContainer,section[data-testid="stBottom"]>div{
    background:#070b14!important;
    border-top:1px solid rgba(48,54,61,0.4)!important
}

/* ── Chat input ── */
[data-testid="stChatInput"]{
    background:#111827!important;
    border:1.5px solid rgba(79,110,247,0.25)!important;
    border-radius:14px!important;
    box-shadow:0 2px 16px rgba(0,0,0,0.5)!important;
    transition:border-color .2s,box-shadow .2s!important
}
[data-testid="stChatInput"]:focus-within{
    border-color:rgba(79,110,247,0.65)!important;
    box-shadow:0 0 0 3px rgba(79,110,247,0.12),0 2px 16px rgba(0,0,0,0.5)!important
}
[data-testid="stChatInput"] textarea{
    background:transparent!important;color:#e6edf3!important;
    font-family:'Inter',sans-serif!important;font-size:0.92rem!important;
    caret-color:#4f6ef7!important
}
[data-testid="stChatInput"] textarea::placeholder{color:#3d4a5c!important}
[data-testid="stChatInput"] button{
    background:linear-gradient(135deg,#4f6ef7,#7c3aed)!important;
    border-radius:10px!important;border:none!important;color:white!important
}

/* ── Chat messages ── */
[data-testid="stChatMessage"]{
    background:#0b1120!important;
    border:1px solid rgba(48,54,61,0.5)!important;
    border-radius:14px!important;
    padding:0.85rem 1.1rem!important;
    margin-bottom:0.5rem!important;
    transition:border-color .18s!important
}
[data-testid="stChatMessage"]:hover{border-color:rgba(79,110,247,0.2)!important}

/* ── Hide ugly default avatars ── */
[data-testid="chatAvatarIcon-user"],[data-testid="chatAvatarIcon-assistant"]{display:none!important}

/* ── Tiny feedback / PDF buttons inside messages ── */
[data-testid="stChatMessage"] .stButton>button{
    padding:0.05rem 0.4rem!important;font-size:0.73rem!important;
    min-height:0!important;height:1.4rem!important;line-height:1.4!important;
    border-radius:6px!important;background:rgba(22,32,50,0.9)!important;
    border:1px solid rgba(48,54,61,0.65)!important;color:#6b7a99!important;width:auto!important
}
[data-testid="stChatMessage"] .stButton>button:hover{
    background:rgba(79,110,247,0.15)!important;color:#c9d1d9!important;
    border-color:rgba(79,110,247,0.4)!important
}
[data-testid="stChatMessage"] [data-testid="stDownloadButton"] button{
    padding:0.05rem 0.4rem!important;font-size:0.73rem!important;height:1.4rem!important;
    background:rgba(79,110,247,0.1)!important;border:1px solid rgba(79,110,247,0.3)!important;
    color:#7b9cff!important;border-radius:6px!important;width:auto!important
}

/* ── Sidebar ── */
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0a0f1c,#070b14)!important;
    border-right:1px solid rgba(48,54,61,0.4)!important
}
[data-testid="stSidebar"] .stMarkdown h3{
    color:#4f6ef7;font-size:0.67rem;font-weight:700;
    letter-spacing:.1em;text-transform:uppercase;margin:1rem 0 0.35rem
}
[data-testid="stSidebar"] .stButton>button{
    width:100%;background:transparent;color:#6b7a99;
    border:1px solid rgba(48,54,61,0.45);border-radius:8px;
    font-size:0.8rem;padding:0.36rem 0.7rem;text-align:left;
    transition:all .18s;margin-bottom:2px
}
[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(79,110,247,0.1);color:#e6edf3;border-color:rgba(79,110,247,0.35)
}

/* ── Selectbox ── */
[data-testid="stSelectbox"]>div>div,[data-testid="stSidebar"] .stSelectbox>div>div{
    background:#111827!important;border:1px solid rgba(48,54,61,0.65)!important;
    color:#e6edf3!important;border-radius:8px!important
}

/* ── Text inputs ── */
.stTextInput>div>div>input{
    background:#111827!important;border:1px solid rgba(48,54,61,0.65)!important;
    color:#e6edf3!important;border-radius:8px!important
}
.stTextInput>div>div>input:focus{
    border-color:rgba(79,110,247,0.5)!important;
    box-shadow:0 0 0 2px rgba(79,110,247,0.1)!important
}

/* ── Primary button ── */
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#4f6ef7,#7c3aed)!important;
    color:white!important;border:none!important;border-radius:10px!important;
    font-weight:600!important;padding:0.5rem 1.4rem!important;transition:all .22s!important
}
.stButton>button[kind="primary"]:hover{
    transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(79,110,247,0.35)!important
}

/* ── Expander ── */
[data-testid="stExpander"] summary,.streamlit-expanderHeader{
    background:#111827!important;border-radius:8px!important;
    color:#8b949e!important;font-size:0.79rem!important
}
[data-testid="stExpander"]{border:1px solid rgba(48,54,61,0.45)!important;border-radius:8px!important}

/* ── Alerts ── */
.stAlert{border-radius:10px!important}

/* ── File uploader ── */
[data-testid="stFileUploader"]{
    background:#111827;border:2px dashed rgba(79,110,247,0.22);border-radius:10px;padding:.4rem
}

/* ── Logo card ── */
.logo-card{
    background:linear-gradient(135deg,rgba(79,110,247,0.1),rgba(124,58,237,0.07));
    border:1px solid rgba(79,110,247,0.18);border-radius:12px;
    padding:.9rem;text-align:center;margin-bottom:.7rem
}
.logo-card h2{color:#e6edf3;margin:0;font-size:.92rem;font-weight:700}
.logo-card p{color:#6b7a99;margin:.12rem 0 0;font-size:.7rem}

/* ── Badge ── */
.badge{display:inline-block;padding:.1rem .48rem;border-radius:999px;font-size:.67rem;font-weight:600}
.badge-blue {background:rgba(79,110,247,.18);color:#7b9cff}
.badge-green{background:rgba(16,185,129,.18);color:#34d399}
.badge-red  {background:rgba(239,68,68,.18); color:#f87171}

/* ── Topbar ── */
.topbar{display:flex;align-items:center;justify-content:space-between;
    padding:.35rem 0 .75rem;border-bottom:1px solid rgba(48,54,61,0.45);margin-bottom:.75rem}
.topbar-title{font-size:.98rem;font-weight:700;color:#e6edf3}
.topbar-user{font-size:.76rem;color:#6b7a99}

/* ── Role labels in chat ── */
.msg-label-user{font-size:.68rem;font-weight:700;color:#7b9cff;
    text-transform:uppercase;letter-spacing:.07em;margin-bottom:.3rem}
.msg-label-ai{font-size:.68rem;font-weight:700;color:#34d399;
    text-transform:uppercase;letter-spacing:.07em;margin-bottom:.3rem}

/* ── Dataframe ── */
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
</style>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "authenticated":  False,
        "user":           None,
        "conv_id":        None,
        "messages":       [],   # [{role, content, sources}]
        "rag_chain":      None,
        "module":         "All Modules",
        "show_login":     True,  # False = show register
        "api_key":        GROK_API_KEY,
        "page":           "chat",   # "chat" | "analytics"
        "admin_view_all": False,    # admin: toggle to see all users' convs
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
        is_admin = user["role"] == "admin"

        st.markdown(f"""
        <div style='text-align:center; margin-bottom:0.8rem;'>
            <span style='font-size:0.8rem; color:#8b949e;'>
                👤 {user['username']}
                <span class='badge badge-{"blue" if is_admin else "green"}'>{user['role']}</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Admin nav buttons ──────────────────────────────────────────────────────
        if is_admin:
            acol1, acol2 = st.columns(2)
            with acol1:
                if st.session_state.page != "analytics":
                    if st.button("📊 Analytics", use_container_width=True, key="nav_analytics"):
                        st.session_state.page = "analytics"
                        st.rerun()
                else:
                    if st.button("💬 Chat", use_container_width=True, key="nav_chat"):
                        st.session_state.page = "chat"
                        st.rerun()
            with acol2:
                label = "👥 All Users" if not st.session_state.admin_view_all else "👤 My Chats"
                if st.button(label, use_container_width=True, key="admin_toggle"):
                    st.session_state.admin_view_all = not st.session_state.admin_view_all
                    st.rerun()

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

        # Conversation history — role-based (#15)
        st.markdown("### 💬 Conversations")
        if is_admin and st.session_state.admin_view_all:
            convs = get_all_conversations_admin()
            st.caption("👥 Showing all users' conversations")
        else:
            convs = get_user_conversations(user["id"])

        if not convs:
            st.caption("No conversations yet.")
        for conv in convs:
            c1, c2 = st.columns([5, 1])
            with c1:
                if is_admin and st.session_state.admin_view_all:
                    label = f"[{conv.get('username','?')}] {conv['title'] or 'New Chat'}"
                else:
                    label = conv["title"] or "New Chat"
                active = conv["id"] == st.session_state.conv_id
                if st.button(f"{'▶ ' if active else ''}{label}", key=f"conv_{conv['id']}", use_container_width=True):
                    load_conversation(conv["id"])
                    st.session_state.page = "chat"
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

        # ── Export Conversation (#10 / #14) ──────────────────────────────
        st.markdown("### 💾 Export Conversation")
        messages = st.session_state.get("messages", [])
        if not messages:
            st.caption("No messages to export yet.")
        else:
            ts    = datetime.now().strftime('%Y%m%d_%H%M')
            uname = st.session_state.user['username']
            mod   = st.session_state.module

            # PDF (#10)
            try:
                pdf_bytes = export_to_pdf(messages, uname, mod)
                st.download_button(
                    label="⬇️ Download as PDF",
                    data=pdf_bytes,
                    file_name=f"payglobal_chat_{ts}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="dl_pdf",
                )
            except Exception as e:
                st.caption(f"⚠️ PDF error: {e}")

            # Word (.docx) (#14)
            try:
                docx_bytes = export_to_docx(messages, uname, mod)
                st.download_button(
                    label="⬇️ Download as Word (.docx)",
                    data=docx_bytes,
                    file_name=f"payglobal_chat_{ts}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="dl_docx",
                )
            except Exception as e:
                st.caption(f"⚠️ Word error: {e}")

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
                    col_up, col_dn, col_pdf, col_spacer = st.columns([1, 1, 2, 6])
                    with col_up:
                        if st.button("👍", key=f"up_{msg_id}_{idx}", help="Good answer"):
                            save_feedback(msg_id, st.session_state.user["id"], 1)
                            st.toast("Thanks for your feedback!", icon="👍")
                    with col_dn:
                        if st.button("👎", key=f"dn_{msg_id}_{idx}", help="Bad answer"):
                            save_feedback(msg_id, st.session_state.user["id"], -1)
                            st.toast("Feedback recorded — we'll improve!", icon="👎")
                    with col_pdf:
                        # Per-answer PDF export (#10)
                        try:
                            ans_pdf = export_answer_pdf(
                                msg["content"],
                                msg.get("sources", []),
                                st.session_state.user["username"],
                            )
                            st.download_button(
                                label="📄 PDF",
                                data=ans_pdf,
                                file_name=f"payglobal_answer_{msg_id}.pdf",
                                mime="application/pdf",
                                key=f"pdf_{msg_id}_{idx}",
                                help="Download this answer as PDF",
                            )
                        except Exception:
                            pass

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
    user    = st.session_state.user

    # ── Rate limiting (#12) — skip for admins ──
    if user["role"] != "admin":
        count = get_request_count_last_hour(user["id"])
        if count >= RATE_LIMIT_PER_HOUR:
            st.warning(
                f"⏳ Rate limit reached: you can send up to **{RATE_LIMIT_PER_HOUR} messages per hour**. "
                f"You've sent **{count}** in the last 60 minutes. Please wait before trying again."
            )
            return

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
                err = str(e).lower()
                if any(k in err for k in ("auth", "api key", "invalid", "incorrect", "401")):
                    st.error("🔑 Invalid API key — please update it in the sidebar and try again.")
                else:
                    st.error("⚠️ Could not start the AI engine. Please check your API key in the sidebar.")
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
                err = str(e).lower()
                if any(k in err for k in ("auth", "api key", "invalid", "incorrect", "401", "403")):
                    answer = (
                        "🔑 **Invalid API Key**\n\n"
                        "Your Grok API key doesn't seem to be working. "
                        "Please update it in the sidebar under **🔑 Grok API Key** and try again.\n\n"
                        "You can get a key at [console.x.ai](https://console.x.ai/)."
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
# ANALYTICS DASHBOARD — admin only (#13)
# ══════════════════════════════════════════════════════════════════════════
def show_analytics():
    """Admin-only analytics dashboard with usage stats and charts."""
    user = st.session_state.user
    if user["role"] != "admin":
        st.error("⛔ Access denied. Admin only.")
        return

    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("""
    <div class='topbar'>
        <span class='topbar-title'>📊 Analytics Dashboard</span>
        <span class='topbar-user'>Admin view · Real-time data</span>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading analytics…"):
        data = get_analytics_data()

    # ── KPI cards ──────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    kpi_style = (
        "background:#0d1117; border:1px solid rgba(48,54,61,0.8); "
        "border-radius:12px; padding:1.2rem; text-align:center;"
    )
    def kpi(col, icon, label, value, color="#4f6ef7"):
        col.markdown(f"""
        <div style='{kpi_style}'>
            <div style='font-size:1.8rem;'>{icon}</div>
            <div style='font-size:2rem; font-weight:700; color:{color};'>{value}</div>
            <div style='font-size:0.78rem; color:#8b949e; margin-top:0.2rem;'>{label}</div>
        </div>
        """, unsafe_allow_html=True)

    kpi(k1, "👥", "Total Users",          data["total_users"],         "#4f6ef7")
    kpi(k2, "💬", "Conversations",         data["total_conversations"], "#10b981")
    kpi(k3, "📨", "Total Messages",        data["total_messages"],      "#f59e0b")
    kpi(k4, "❓", "User Questions",        data["total_questions"],     "#ef4444")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Daily activity chart ───────────────────────────────────────────────
    col_chart, col_pie = st.columns([3, 2])

    with col_chart:
        st.markdown("#### 📅 Questions per Day (Last 14 Days)")
        daily = data.get("daily_messages", [])
        if daily:
            days  = [d["day"]  for d in daily]
            cnts  = [d["cnt"]  for d in daily]
            fig = go.Figure(go.Bar(
                x=days, y=cnts,
                marker_color="#4f6ef7",
                marker_line_color="rgba(79,110,247,0.3)",
                marker_line_width=1,
            ))
            fig.update_layout(
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                font=dict(color="#e6edf3", size=11),
                xaxis=dict(gridcolor="rgba(48,54,61,0.5)", tickangle=-35),
                yaxis=dict(gridcolor="rgba(48,54,61,0.5)"),
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No activity data yet.")

    with col_pie:
        st.markdown("#### 📦 Module Usage")
        modules = data.get("module_usage", [])
        if modules:
            labels = [m["module"] for m in modules]
            values = [m["cnt"]    for m in modules]
            fig2 = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.45,
                marker=dict(colors=px.colors.qualitative.Plotly),
                textfont=dict(size=11),
            ))
            fig2.update_layout(
                paper_bgcolor="#0d1117",
                font=dict(color="#e6edf3", size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
                showlegend=True,
                legend=dict(bgcolor="#0d1117", font=dict(size=10)),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No module data yet.")

    # ── Feedback + Top Users ───────────────────────────────────────────────
    col_fb, col_users = st.columns([1, 2])

    with col_fb:
        st.markdown("#### 👍 Feedback Satisfaction")
        fb = data.get("feedback", {})
        total_fb = fb.get("total", 0)
        up  = fb.get("thumbs_up",   0) or 0
        dn  = fb.get("thumbs_down", 0) or 0
        if total_fb:
            pct = round(up / total_fb * 100)
            fig3 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct,
                number={"suffix": "%", "font": {"color": "#e6edf3", "size": 32}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                    "bar":  {"color": "#10b981"},
                    "bgcolor": "#161b27",
                    "steps": [
                        {"range": [0,  50], "color": "rgba(239,68,68,0.15)"},
                        {"range": [50, 75], "color": "rgba(245,158,11,0.15)"},
                        {"range": [75,100], "color": "rgba(16,185,129,0.15)"},
                    ],
                },
            ))
            fig3.update_layout(
                paper_bgcolor="#0d1117",
                font=dict(color="#e6edf3"),
                margin=dict(l=10, r=10, t=20, b=10),
                height=220,
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown(
                f"<div style='text-align:center; font-size:0.8rem; color:#8b949e;'>"
                f"👍 {up} &nbsp;|&nbsp; 👎 {dn} &nbsp;|&nbsp; Total {total_fb}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No feedback yet.")

    with col_users:
        st.markdown("#### 🏆 Most Active Users")
        top_users = data.get("top_users", [])
        if top_users:
            import pandas as pd
            df = pd.DataFrame(top_users)
            df.columns = ["Username", "Questions Asked"]
            df.index   = df.index + 1
            st.dataframe(df, use_container_width=True, height=230)
        else:
            st.info("No user activity yet.")

    st.divider()

    # ── User management table ──────────────────────────────────────────────
    st.markdown("#### 👤 Registered Users")
    all_users = get_all_users()
    if all_users:
        import pandas as pd
        udf = pd.DataFrame(all_users)[["username", "email", "role", "created_at", "last_login"]]
        udf.columns = ["Username", "Email", "Role", "Registered", "Last Login"]
        udf.index   = udf.index + 1
        st.dataframe(udf, use_container_width=True)
    else:
        st.info("No users found.")


# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    show_login_page()
else:
    show_sidebar()
    if st.session_state.page == "analytics":
        show_analytics()
    else:
        show_chat()
