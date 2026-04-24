"""
PayGlobal AI Assistant — Streamlit Application
"""
import streamlit as st

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
    get_user_conversations, delete_conversation,
    save_feedback, get_all_conversations_admin, get_analytics_data,
    get_all_users,
    delete_user, update_user_role, reset_user_password, get_recent_audit_log,
)
from ingest import ingest_file
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
