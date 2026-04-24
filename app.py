"""
PayGlobal AI Assistant — Streamlit Application
"""
import streamlit as st
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
    delete_user, update_user_role, reset_user_password, get_recent_audit_log,
)
from ingest import ingest_file, index_exists
from rag_chain import get_rag_chain, ask
from utils.exporter import export_to_pdf, export_to_docx, export_answer_pdf
from ui.theme import apply_theme as apply_enterprise_theme
from services.state import init_state as init_app_state
from ui.auth_view import render_login_page
from ui.sidebar_view import render_sidebar
from ui.analytics_view import render_analytics
from ui.admin_view import render_admin_panel
from services.chat_service import (
    load_chain as load_chain_service,
    start_new_conversation as start_new_conversation_service,
    load_conversation as load_conversation_service,
    auto_title as auto_title_service,
    handle_message as handle_message_service,
)

# Bootstrap DB + admin account on every cold start
bootstrap_admin()

# ══════════════════════════════════════════════════════════════════════════
# THEME CSS — dark / light switching
# ══════════════════════════════════════════════════════════════════════════
_CSS_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
#MainMenu,footer{visibility:hidden}
[data-testid="stAppDeployButton"]{display:none!important}
.viewerBadge_container__r5tak,.viewerBadge_link__qRIco{display:none!important}
header[data-testid="stHeader"]{background:transparent!important}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{visibility:hidden!important}
.block-container{padding:0.8rem 1.5rem 0 1.5rem!important;max-width:100%!important}
.status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:middle}
.status-dot.green{background:#10b981;box-shadow:0 0 6px rgba(16,185,129,0.7)}
.status-dot.red{background:#ef4444;box-shadow:0 0 6px rgba(239,68,68,0.7)}
.status-dot.amber{background:#f59e0b;box-shadow:0 0 6px rgba(245,158,11,0.7)}
.badge{display:inline-block;padding:.1rem .48rem;border-radius:999px;font-size:.67rem;font-weight:600}
.badge-blue{background:rgba(79,110,247,.18);color:#4f6ef7}
.badge-green{background:rgba(16,185,129,.18);color:#10b981}
.badge-red{background:rgba(239,68,68,.18);color:#ef4444}
[data-testid="collapsedControl"]{
    display:flex!important;visibility:visible!important;opacity:1!important;
    background:rgba(79,110,247,0.12)!important;
    border:1px solid rgba(79,110,247,0.35)!important;
    border-left:none!important;border-radius:0 12px 12px 0!important;
    padding:10px 8px!important;box-shadow:none!important;
    z-index:999999!important}
[data-testid="collapsedControl"] svg{fill:#7b9cff!important}
[data-testid="collapsedControl"]:hover{background:rgba(79,110,247,0.2)!important}
.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#4f6ef7,#7c3aed)!important;
    color:white!important;border:none!important;border-radius:10px!important;
    font-weight:600!important;transition:all .22s!important}
.stButton>button[kind="primary"]:hover{
    transform:translateY(-1px)!important;box-shadow:0 6px 20px rgba(79,110,247,0.35)!important}
.stat-chip{display:flex;flex-direction:column;align-items:center;border-radius:10px;padding:.45rem .3rem;flex:1}
.stat-chip .val{font-size:1.1rem;font-weight:700;color:#4f6ef7}
.stat-chip .lbl{font-size:.6rem;margin-top:.1rem;text-align:center}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:.35rem 0 .75rem;margin-bottom:.75rem}
.topbar-title{font-size:.98rem;font-weight:700}
.topbar-user{font-size:.76rem}
.msg-label-user{font-size:.68rem;font-weight:700;color:#7b9cff;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.3rem}
.msg-label-ai{font-size:.68rem;font-weight:700;color:#10b981;text-transform:uppercase;letter-spacing:.07em;margin-bottom:.3rem}
[data-testid="chatAvatarIcon-user"],[data-testid="chatAvatarIcon-assistant"]{display:none!important}
.stAlert{border-radius:10px!important}
[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
.logo-card{border-radius:12px;padding:.9rem;text-align:center;margin-bottom:.7rem}
.logo-card h2{margin:0;font-size:.92rem;font-weight:700}
.logo-card p{margin:.12rem 0 0;font-size:.7rem}
.stTabs [data-baseweb="tab-list"]{border-radius:10px!important;gap:2px!important}
.stTabs [data-baseweb="tab"]{border-radius:8px!important;font-size:0.82rem!important;font-weight:500!important}

/* ── Sidebar section label ── */
.sb-section-label{
    font-size:.58rem;font-weight:700;letter-spacing:.12em;
    text-transform:uppercase;color:#4f6ef7;
    margin:.7rem 0 .2rem;opacity:.85
}

/* ── Sidebar compact header ── */
.sb-header{
    display:flex;align-items:center;
    padding:.4rem 0 .5rem;
    border-bottom:1px solid rgba(48,54,61,0.35);
    margin-bottom:.5rem
}
.sb-header .sb-logo{font-size:.92rem;font-weight:700;margin-left:.4rem}
.sb-header .sb-sub{font-size:.63rem;color:#6b7a99;margin-left:.4rem}

/* ── Prompt chip buttons \u2014 auto-width, pill-shaped ── */
div[data-testid="stColumns"] div[data-testid="stButton"] button[kind="secondary"][id^="ex_"],
div[data-testid="stColumns"] div[data-testid="stButton"] button:has(+ *[id^="ex_"]) {
    width:auto!important;white-space:nowrap!important;
    padding:.4rem .85rem!important;
    border-radius:999px!important;
    border:1px solid rgba(79,110,247,0.4)!important;
    background:rgba(79,110,247,0.07)!important;
    color:#9ab0ff!important;
    font-size:.8rem!important;
    transition:all .18s!important;
}
/* Target by key prefix \u2014 Streamlit generates id from key */
[data-testid="stButton"] button[kind="secondary"]:not([data-testid]) {
    width:fit-content!important;
}
"""

_CSS_DARK = """
.stApp{background:#070b14!important;color:#e6edf3!important}
[data-testid="stBottom"],[data-testid="stChatInputContainer"],section[data-testid="stBottom"]>div{
    background:#070b14!important;border-top:1px solid rgba(48,54,61,0.4)!important}
[data-testid="stChatInput"]{
    background:#111827!important;border:1.5px solid rgba(79,110,247,0.25)!important;
    border-radius:14px!important;box-shadow:0 2px 16px rgba(0,0,0,0.5)!important}
[data-testid="stChatInput"]:focus-within{border-color:rgba(79,110,247,0.65)!important}
[data-testid="stChatInput"] textarea{background:transparent!important;color:#e6edf3!important;caret-color:#4f6ef7!important}
[data-testid="stChatInput"] textarea::placeholder{color:#3d4a5c!important}
[data-testid="stChatInput"] button{background:linear-gradient(135deg,#4f6ef7,#7c3aed)!important;border-radius:10px!important;color:white!important}
[data-testid="stChatMessage"]{
    background:#0b1120!important;border:1px solid rgba(48,54,61,0.5)!important;
    border-radius:14px!important;padding:0.85rem 1.1rem!important;margin-bottom:0.5rem!important}
[data-testid="stChatMessage"]:hover{border-color:rgba(79,110,247,0.2)!important}
[data-testid="stChatMessage"] .stButton>button{
    background:rgba(22,32,50,0.9)!important;border:1px solid rgba(48,54,61,0.65)!important;color:#6b7a99!important}
[data-testid="stChatMessage"] .stButton>button:hover{
    background:rgba(79,110,247,0.15)!important;color:#c9d1d9!important}
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0a0f1c,#070b14)!important;
    border-right:1px solid rgba(48,54,61,0.4)!important}
[data-testid="stSidebar"] .stMarkdown h3{
    color:#4f6ef7;font-size:0.67rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:1rem 0 0.35rem}
[data-testid="stSidebar"] .stButton>button{
    background:transparent;color:#6b7a99;border:1px solid rgba(48,54,61,0.45);
    border-radius:8px;font-size:0.8rem;transition:all .18s;margin-bottom:2px}
[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(79,110,247,0.1);color:#e6edf3;border-color:rgba(79,110,247,0.35)}
[data-testid="stSelectbox"]>div>div{
    background:#111827!important;border:1px solid rgba(48,54,61,0.65)!important;color:#e6edf3!important;border-radius:8px!important}
.stTextInput>div>div>input{
    background:#111827!important;border:1px solid rgba(48,54,61,0.65)!important;color:#e6edf3!important;border-radius:8px!important}
.stTextInput>div>div>input:focus{border-color:rgba(79,110,247,0.5)!important}
[data-testid="stExpander"] summary{background:#111827!important;border-radius:8px!important;color:#8b949e!important}
[data-testid="stExpander"]{border:1px solid rgba(48,54,61,0.45)!important;border-radius:8px!important}
[data-testid="stFileUploader"]{background:#111827;border:2px dashed rgba(79,110,247,0.22);border-radius:10px;padding:.4rem}
.logo-card{background:linear-gradient(135deg,rgba(79,110,247,0.1),rgba(124,58,237,0.07));border:1px solid rgba(79,110,247,0.18)}
.logo-card h2{color:#e6edf3}.logo-card p{color:#6b7a99}
.stat-chip{background:#0d1117;border:1px solid rgba(48,54,61,0.6)}.stat-chip .lbl{color:#6b7a99}
.topbar{border-bottom:1px solid rgba(48,54,61,0.45)}
.topbar-title{color:#e6edf3}.topbar-user{color:#6b7a99}
.stTabs [data-baseweb="tab-list"]{background:#0d1117!important;border:1px solid rgba(48,54,61,0.5)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#6b7a99!important}
.stTabs [aria-selected="true"]{background:rgba(79,110,247,0.15)!important;color:#7b9cff!important}
"""

_CSS_LIGHT = """
.stApp{background:#f0f2f8!important;color:#1a1f36!important}
[data-testid="stBottom"],[data-testid="stChatInputContainer"],section[data-testid="stBottom"]>div{
    background:#f0f2f8!important;border-top:1px solid rgba(200,210,230,0.7)!important}
[data-testid="stChatInput"]{
    background:#ffffff!important;border:1.5px solid rgba(79,110,247,0.3)!important;
    border-radius:14px!important;box-shadow:0 2px 12px rgba(79,110,247,0.08)!important}
[data-testid="stChatInput"]:focus-within{border-color:rgba(79,110,247,0.7)!important}
[data-testid="stChatInput"] textarea{background:transparent!important;color:#1a1f36!important;caret-color:#4f6ef7!important}
[data-testid="stChatInput"] textarea::placeholder{color:#9ba3c0!important}
[data-testid="stChatInput"] button{background:linear-gradient(135deg,#4f6ef7,#7c3aed)!important;border-radius:10px!important;color:white!important}
[data-testid="stChatMessage"]{
    background:#ffffff!important;border:1px solid rgba(200,210,230,0.8)!important;
    border-radius:14px!important;padding:0.85rem 1.1rem!important;margin-bottom:0.5rem!important;
    box-shadow:0 2px 8px rgba(79,110,247,0.06)!important}
[data-testid="stChatMessage"]:hover{border-color:rgba(79,110,247,0.3)!important}
[data-testid="stChatMessage"] .stButton>button{
    background:rgba(240,242,248,0.9)!important;border:1px solid rgba(200,210,230,0.8)!important;color:#6b7a99!important}
[data-testid="stChatMessage"] .stButton>button:hover{
    background:rgba(79,110,247,0.1)!important;color:#4f6ef7!important}
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#ffffff,#f8f9fc)!important;
    border-right:1px solid rgba(200,210,230,0.7)!important}
[data-testid="stSidebar"] .stMarkdown h3{
    color:#4f6ef7;font-size:0.67rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:1rem 0 0.35rem}
[data-testid="stSidebar"] .stButton>button{
    background:transparent;color:#4a5568;border:1px solid rgba(200,210,230,0.7);
    border-radius:8px;font-size:0.8rem;transition:all .18s;margin-bottom:2px}
[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(79,110,247,0.08);color:#1a1f36;border-color:rgba(79,110,247,0.35)}
[data-testid="stSelectbox"]>div>div{
    background:#ffffff!important;border:1px solid rgba(200,210,230,0.8)!important;color:#1a1f36!important;border-radius:8px!important}
.stTextInput>div>div>input{
    background:#ffffff!important;border:1px solid rgba(200,210,230,0.8)!important;color:#1a1f36!important;border-radius:8px!important}
.stTextInput>div>div>input:focus{border-color:rgba(79,110,247,0.5)!important}
[data-testid="stExpander"] summary{background:#ffffff!important;border-radius:8px!important;color:#4a5568!important}
[data-testid="stExpander"]{border:1px solid rgba(200,210,230,0.7)!important;border-radius:8px!important}
[data-testid="stFileUploader"]{background:#ffffff;border:2px dashed rgba(79,110,247,0.3);border-radius:10px;padding:.4rem}
.logo-card{background:linear-gradient(135deg,rgba(79,110,247,0.07),rgba(124,58,237,0.04));border:1px solid rgba(79,110,247,0.2)}
.logo-card h2{color:#1a1f36}.logo-card p{color:#6b7a99}
.stat-chip{background:#ffffff;border:1px solid rgba(200,210,230,0.7)}.stat-chip .lbl{color:#9ba3c0}
.topbar{border-bottom:1px solid rgba(200,210,230,0.7)}
.topbar-title{color:#1a1f36}.topbar-user{color:#6b7a99}
.stTabs [data-baseweb="tab-list"]{background:#ffffff!important;border:1px solid rgba(200,210,230,0.7)!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#6b7a99!important}
.stTabs [aria-selected="true"]{background:rgba(79,110,247,0.1)!important;color:#4f6ef7!important}
"""


def apply_theme():
    """Inject theme CSS based on st.session_state.theme ('dark' | 'light')."""
    t = st.session_state.get("theme", "dark")
    css = _CSS_DARK if t == "dark" else _CSS_LIGHT
    st.markdown(f"<style>{_CSS_COMMON}{css}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "authenticated":  False,
        "user":           None,
        "conv_id":        None,
        "messages":       [],
        "rag_chain":      None,
        "module":         "All Modules",
        "show_login":     True,
        "api_key":        GROK_API_KEY,
        "page":           "chat",
        "admin_view_all": False,
        "theme":          "dark",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_app_state(GROK_API_KEY)
apply_enterprise_theme()


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════
def load_chain():
    load_chain_service()


def start_new_conversation():
    start_new_conversation_service()


def load_conversation(conv_id: int):
    load_conversation_service(conv_id)



def auto_title(conv_id: int, first_user_msg: str):
    auto_title_service(conv_id, first_user_msg)


# ══════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════
def show_login_page():
    render_login_page(login_fn=login, register_fn=register, default_api_key=GROK_API_KEY)


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════
def show_sidebar():
    render_sidebar(
        modules=PAYGLOBAL_MODULES,
        uploads_dir=UPLOADS_DIR,
        ingest_file_fn=ingest_file,
        export_to_pdf_fn=export_to_pdf,
        export_to_docx_fn=export_to_docx,
        get_analytics_data_fn=get_analytics_data,
        get_all_conversations_admin_fn=get_all_conversations_admin,
        get_user_conversations_fn=get_user_conversations,
        delete_conversation_fn=delete_conversation,
        start_new_conversation_fn=start_new_conversation,
        load_conversation_fn=load_conversation,
    )


# ══════════════════════════════════════════════════════════════════════════
# MAIN CHAT INTERFACE
# ══════════════════════════════════════════════════════════════════════════
def show_chat():
    user     = st.session_state.user
    is_admin = user["role"] == "admin"

    # API status check (admin only, cached per key prefix)
    if "api_status" not in st.session_state:
        st.session_state.api_status = "unknown"

    if is_admin and st.session_state.api_key:
        if st.session_state.get("_last_status_check") != st.session_state.api_key[:8]:
            try:
                import requests as _rq
                from config import GROK_BASE_URL, GROK_MODEL
                r = _rq.post(
                    GROK_BASE_URL.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {st.session_state.api_key}",
                             "Content-Type": "application/json"},
                    json={"model": GROK_MODEL,
                          "messages": [{"role": "user", "content": "ping"}],
                          "max_tokens": 1},
                    timeout=5,
                )
                st.session_state.api_status = (
                    "green" if r.status_code in (200, 201)
                    else "amber" if "credits" in r.text.lower()
                    else "red"
                )
            except Exception:
                st.session_state.api_status = "red"
            st.session_state._last_status_check = st.session_state.api_key[:8]

    # Build topbar HTML pieces safely — no nested angle brackets inside f-strings
    from config import GROK_MODEL as _MDL
    _module = st.session_state.module

    if is_admin:
        _sdot  = st.session_state.api_status
        _slbl  = {"green": "AI Online", "amber": "No Credits",
                  "red": "Offline", "unknown": "Connecting…"}.get(_sdot, "")
        _scol  = {"green": "#10b981", "amber": "#f59e0b",
                  "red": "#ef4444", "unknown": "#4b5563"}.get(_sdot, "#4b5563")
        _status = (
            "<span style='display:inline-flex;align-items:center;gap:.35rem;'>"
            f"<span style='width:7px;height:7px;border-radius:50%;background:{_scol};"
            f"display:inline-block;box-shadow:0 0 5px {_scol};'></span>"
            f"<span style='font-size:.72rem;color:#6b7a99;'>{_slbl}</span></span>"
        )
        _model_lbl = _MDL.split("/")[-1]
        _model = (
            f"<span style='font-size:.65rem;color:#3d4a5c;padding:.1rem .4rem;"
            f"border:1px solid rgba(48,54,61,0.45);border-radius:5px;'>{_model_lbl}</span>"
        )
    else:
        _status = ""
        _model  = ""

    _module_html = (
        f"<span style='font-size:.76rem;'>Module: "
        f"<b style='color:#4f6ef7;'>{_module}</b></span>"
    )

    st.markdown(
        "<div class='topbar'>"
        f"<span class='topbar-title'>🌐 {APP_TITLE}</span>"
        f"<span class='topbar-user' style='display:flex;align-items:center;gap:.8rem;'>"
        f"{_status}{_module_html}{_model}"
        f"</span></div>",
        unsafe_allow_html=True,
    )


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
            <p style='font-size:0.9rem;'>Installation &middot; Configuration &middot; Troubleshooting &middot; Functional Guidance</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Compact prompt chips (auto-width, centered) ──────────────────────
        example_prompts = [
            "How do I install the PayGlobal Payroll module?",
            "Configure ESS portal step by step",
            "Fix database connection error during setup",
            "Setup employee master data",
        ]
        # Render as HTML chips — Streamlit buttons always stretch, so use form submit trick
        st.markdown("""
        <style>
        .chip-row{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin:.4rem 0}
        .prompt-chip{
            display:inline-flex;align-items:center;gap:.35rem;
            padding:.42rem .85rem;
            border-radius:999px;
            border:1px solid rgba(79,110,247,0.4);
            background:rgba(79,110,247,0.07);
            color:#9ab0ff;
            font-size:.8rem;
            font-family:'Inter',sans-serif;
            cursor:pointer;
            white-space:nowrap;
            transition:all .18s;
            outline:none;
        }
        .prompt-chip:hover{
            background:rgba(79,110,247,0.18);
            border-color:rgba(79,110,247,0.7);
            color:#c8d8ff;
            transform:translateY(-1px);
        }
        </style>
        """, unsafe_allow_html=True)

        # Use Streamlit columns trick: 4 equal columns, each holds one centered chip
        chip_cols = st.columns(4)
        for i, prompt in enumerate(example_prompts):
            with chip_cols[i]:
                if st.button(f"💡 {prompt}", key=f"ex_{i}"):
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
        "Ask about PayGlobal implementation, configuration, or troubleshooting...",
    ) or pending

    if user_input:
        _handle_message(user_input)


def _handle_message(user_input: str):
    handle_message_service(user_input)


# ══════════════════════════════════════════════════════════════════════════
# ANALYTICS DASHBOARD — admin only (#13)
# ══════════════════════════════════════════════════════════════════════════
def show_analytics():
    """Admin-only analytics dashboard with usage stats and charts."""
    return render_analytics(
        get_analytics_data_fn=get_analytics_data,
        get_all_users_fn=get_all_users,
    )
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
# ADMIN CONTROL PANEL
# ══════════════════════════════════════════════════════════════════════════
def show_admin_panel():
    """Comprehensive admin control panel — 6 management tabs."""
    return render_admin_panel(
        uploads_dir=UPLOADS_DIR,
        rate_limit_per_hour=RATE_LIMIT_PER_HOUR,
        get_analytics_data_fn=get_analytics_data,
        get_all_users_fn=get_all_users,
        update_user_role_fn=update_user_role,
        reset_user_password_fn=reset_user_password,
        delete_user_fn=delete_user,
        get_recent_audit_log_fn=get_recent_audit_log,
    )
    user = st.session_state.user
    if user["role"] != "admin":
        st.error("⛔ Access denied. Admin only."); return

    from auth import hash_password, register as auth_register
    from config import GROK_BASE_URL, GROK_MODEL, SYSTEM_PROMPT_PATH, FAISS_INDEX_DIR, ALLOW_DANGEROUS_DESERIALIZATION
    from pathlib import Path

    st.markdown("""
    <div class='topbar'>
        <span class='topbar-title'>⚙️ Admin Control Panel</span>
        <span class='topbar-user'>Full backend control · Admin only</span>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["🏥 System Health", "👤 User Management",
                    "📚 Knowledge Base", "⚙️ Model Config",
                    "✏️ Prompt Editor",  "📋 Audit Log"])

    # ── Tab 1: System Health ──────────────────────────────────────────────
    with tabs[0]:
        from ingest import index_exists
        idx_ok = index_exists()

        st.markdown("#### 🔍 Live Status")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Vector Index",  "✅ Ready"   if idx_ok else "❌ Missing")
        sc2.metric("LLM Model",     GROK_MODEL.split("/")[-1])
        sc3.metric("API Provider",  "Groq (free)" if "groq" in GROK_BASE_URL else "xAI")

        faiss_chunks = 0
        if idx_ok:
            try:
                from langchain_community.vectorstores import FAISS
                from rag_chain import _get_embeddings
                vs = FAISS.load_local(str(FAISS_INDEX_DIR), _get_embeddings(),
                                      allow_dangerous_deserialization=ALLOW_DANGEROUS_DESERIALIZATION)
                faiss_chunks = vs.index.ntotal
            except Exception:
                pass
        sc4.metric("Indexed Chunks", faiss_chunks)

        st.divider()
        data = get_analytics_data()
        st.markdown("#### 📊 Database Totals")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Users",          data["total_users"])
        d2.metric("Conversations",  data["total_conversations"])
        d3.metric("Messages",       data["total_messages"])
        d4.metric("User Questions", data["total_questions"])

        st.divider()
        fb = data.get("feedback", {})
        if fb.get("total", 0):
            up, dn = fb.get("thumbs_up", 0) or 0, fb.get("thumbs_down", 0) or 0
            pct = round(up / fb["total"] * 100)
            st.markdown(
                f"**Feedback satisfaction:** 👍 {up} &nbsp;|&nbsp; 👎 {dn} &nbsp;→&nbsp; "
                f"<span style='color:#10b981;font-weight:700;'>{pct}% positive</span>",
                unsafe_allow_html=True,
            )
        st.info(f"⏱️ Rate limit: **{RATE_LIMIT_PER_HOUR} req/hr** per user. Admins are always exempt.")

    # ── Tab 2: User Management ────────────────────────────────────────────
    with tabs[1]:
        st.markdown("#### 👥 Registered Users")
        all_users = get_all_users()

        for u in all_users:
            is_me = u["id"] == user["id"]
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2.2, 2.5, 1.5, 2.8, 0.8])
                badge = "🔵" if u["role"] == "admin" else "⚪"
                c1.markdown(f"{badge} **{u['username']}** {'*(you)*' if is_me else ''}")
                c2.markdown(f"`{u.get('email') or '—'}`")

                with c3:
                    if not is_me:
                        sel = st.selectbox("", ["user", "admin"],
                                           index=0 if u["role"] == "user" else 1,
                                           key=f"rsel_{u['id']}",
                                           label_visibility="collapsed")
                        if sel != u["role"]:
                            update_user_role(u["id"], sel)
                            st.toast(f"✅ {u['username']} → {sel}"); st.rerun()
                    else:
                        st.caption(f"`{u['role']}`")

                with c4:
                    if not is_me:
                        np_ = st.text_input("", key=f"npw_{u['id']}",
                                            placeholder="New password…", type="password",
                                            label_visibility="collapsed")
                        if st.button("🔑 Reset", key=f"rpw_{u['id']}", use_container_width=True):
                            if np_ and len(np_) >= 6:
                                reset_user_password(u["id"], hash_password(np_))
                                st.toast(f"🔑 Password reset for {u['username']}")
                            else:
                                st.warning("Min 6 characters required.")

                with c5:
                    if not is_me:
                        if st.button("🗑️", key=f"delu_{u['id']}", help=f"Delete {u['username']}"):
                            delete_user(u["id"])
                            st.toast(f"🗑️ Deleted {u['username']}"); st.rerun()
            st.divider()

        st.markdown("#### ➕ Create New User")
        with st.form("admin_create_user", clear_on_submit=True):
            nu1, nu2 = st.columns(2)
            with nu1:
                nu_user  = st.text_input("Username", placeholder="Enter username")
                nu_email = st.text_input("Email",    placeholder="user@company.com")
            with nu2:
                nu_pw   = st.text_input("Password", placeholder="Min 8 chars", type="password")
                nu_role = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("➕ Create User", type="primary"):
                if nu_user and nu_pw and len(nu_pw) >= 8:
                    try:
                        auth_register(nu_user, nu_pw, nu_email, nu_role)
                        st.success(f"✅ User **{nu_user}** created as `{nu_role}`")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.error("Username required and password must be ≥ 8 characters.")

    # ── Tab 3: Knowledge Base ─────────────────────────────────────────────
    with tabs[2]:
        from ingest import ingest_file, index_exists
        st.markdown("#### 📂 Uploaded Files")

        files = sorted(UPLOADS_DIR.glob("*.*"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            st.info("No documents uploaded yet. Use the sidebar to upload PDFs/DOCX.")
        else:
            for f in files:
                sz   = f.stat().st_size / 1024
                ts_  = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                fc1, fc2, fc3, fc4 = st.columns([3, 1.2, 1.5, 0.8])
                fc1.markdown(f"📄 `{f.name}`")
                fc2.markdown(f"`{sz:.1f} KB`")
                fc3.markdown(f"`{ts_}`")
                with fc4:
                    if st.button("🗑️", key=f"delf_{f.name}", help=f"Delete {f.name}"):
                        f.unlink()
                        st.toast(f"Deleted {f.name}"); st.rerun()
                st.divider()

        st.markdown("#### ♻️ Re-index All Documents")
        st.caption("Wipes and rebuilds the entire FAISS vector store from all uploaded files.")
        if st.button("⚡ Re-ingest Everything", type="primary", use_container_width=True):
            if files:
                total_chunks, prog = 0, st.progress(0)
                for i, f in enumerate(files):
                    try:
                        total_chunks += ingest_file(f)
                    except Exception as e:
                        st.warning(f"⚠️ {f.name}: {e}")
                    prog.progress((i + 1) / len(files))
                st.session_state.rag_chain = None
                st.success(f"✅ Re-indexed {len(files)} file(s) → {total_chunks} chunks")
            else:
                st.warning("No files to ingest.")

    # ── Tab 4: Model Config ───────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### 🤖 LLM & Rate Limit Configuration")
        GROQ_MODELS = [
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "groq/compound",
            "groq/compound-mini",
        ]
        mc1, mc2 = st.columns([3, 2])
        with mc1:
            cur_idx   = GROQ_MODELS.index(GROK_MODEL) if GROK_MODEL in GROQ_MODELS else 0
            new_model = st.selectbox("LLM Model", GROQ_MODELS, index=cur_idx)
            new_url   = st.text_input("API Base URL", value=GROK_BASE_URL)
            new_rate  = st.number_input("Rate limit (req/hr per user)",
                                        min_value=5, max_value=500,
                                        value=int(RATE_LIMIT_PER_HOUR), step=5)
        with mc2:
            st.markdown("**Free models on Groq:**")
            for m in GROQ_MODELS:
                active = "✅ " if m == GROK_MODEL else "· "
                st.markdown(f"{active}`{m}`")

        if st.button("💾 Apply Config", type="primary", use_container_width=True):
            env_path = Path(__file__).parent / ".env"
            lines    = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
            env_dict = {}
            for line in lines:
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env_dict[k.strip()] = v.strip()
            env_dict["GROK_MODEL"]          = new_model
            env_dict["GROK_BASE_URL"]       = new_url
            env_dict["RATE_LIMIT_PER_HOUR"] = str(int(new_rate))
            env_path.write_text(
                "\n".join(f"{k}={v}" for k, v in env_dict.items()) + "\n",
                encoding="utf-8",
            )
            st.session_state.rag_chain = None
            st.success(
                f"✅ Saved! Model: **{new_model}** · Rate: **{int(new_rate)}/hr**\n\n"
                "⚠️ Restart the app for model/URL changes to fully take effect."
            )

    # ── Tab 5: Prompt Editor ──────────────────────────────────────────────
    with tabs[4]:
        st.markdown("#### ✏️ System Prompt Editor")
        st.caption("Defines the AI's scope, tone, and response style. Saved changes take effect on next question.")
        current_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
        new_prompt = st.text_area("", value=current_prompt, height=380,
                                  label_visibility="collapsed",
                                  placeholder="You are a helpful PayGlobal AI assistant…")
        pe1, pe2 = st.columns(2)
        with pe1:
            if st.button("💾 Save Prompt", type="primary", use_container_width=True):
                SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SYSTEM_PROMPT_PATH.write_text(new_prompt, encoding="utf-8")
                st.session_state.rag_chain = None
                st.success("✅ Prompt saved. AI will use it on the next question.")
        with pe2:
            if st.button("↩️ Reset to Default", use_container_width=True):
                default = (
                    "You are PayGlobal Expert, an AI consultant specialising exclusively in the PayGlobal ERP system.\n\n"
                    "Use the provided context to answer questions about PayGlobal installation, "
                    "configuration, troubleshooting, and functionality.\n\n"
                    "Context:\n{context}\n\n"
                    "Rules:\n"
                    "- Only answer questions related to PayGlobal\n"
                    "- Be precise, structured, and professional\n"
                    "- Use markdown formatting (headers, bullet points, tables) for clarity\n"
                    "- Cite page numbers when available"
                )
                SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SYSTEM_PROMPT_PATH.write_text(default, encoding="utf-8")
                st.session_state.rag_chain = None
                st.success("✅ Reset to default prompt."); st.rerun()

    # ── Tab 6: Audit Log ──────────────────────────────────────────────────
    with tabs[5]:
        import pandas as pd
        st.markdown("#### 📋 Recent User Queries")
        logs = get_recent_audit_log(100)
        if not logs:
            st.info("No activity logged yet.")
        else:
            df = pd.DataFrame(logs)
            df.columns = ["User", "Conversation", "Module", "Role", "Question", "Timestamp"]
            df["Timestamp"] = df["Timestamp"].str[:16]
            df["Question"]  = df["Question"].str[:120] + "…"
            df.index = df.index + 1
            st.dataframe(
                df[["Timestamp", "User", "Module", "Question"]],
                use_container_width=True, height=460,
            )



# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    show_login_page()
else:
    show_sidebar()
    if st.session_state.page == "analytics":
        show_analytics()
    elif st.session_state.page == "admin":
        show_admin_panel()
    else:
        show_chat()
