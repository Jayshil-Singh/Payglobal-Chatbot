import streamlit as st

CSS_COMMON = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important}
#MainMenu,footer{visibility:hidden}
[data-testid="stAppDeployButton"]{display:none!important}
.viewerBadge_container__r5tak,.viewerBadge_link__qRIco{display:none!important}
header[data-testid="stHeader"]{background:transparent!important}
/* Keep toolbar visible so sidebar collapsed control always works */
[data-testid="stDecoration"],[data-testid="stStatusWidget"]{visibility:hidden!important}
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
.sb-section-label{
    font-size:.58rem;font-weight:700;letter-spacing:.12em;
    text-transform:uppercase;color:#4f6ef7;
    margin:.7rem 0 .2rem;opacity:.85
}
"""

CSS_DARK = """
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
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#0a0f1c,#070b14)!important;
    border-right:1px solid rgba(48,54,61,0.4)!important}
"""

CSS_LIGHT = """
.stApp{background:#f0f2f8!important;color:#1a1f36!important}
[data-testid="stToolbar"]{background:transparent!important}
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
[data-testid="stSidebar"] *{color:#1a1f36!important}
[data-testid="stSidebar"] .stButton>button[kind="secondary"]{
    background:#ffffff!important;border:1px solid rgba(180,193,218,0.85)!important;color:#1a1f36!important
}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{
    color:#ffffff!important
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] [data-baseweb="select"]{
    background:#ffffff!important;border-color:rgba(180,193,218,0.9)!important;color:#1a1f36!important
}
[data-testid="stSidebar"]{
    background:linear-gradient(180deg,#ffffff,#f8f9fc)!important;
    border-right:1px solid rgba(200,210,230,0.7)!important}
"""


def apply_theme() -> None:
    theme = st.session_state.get("theme", "dark")
    css = CSS_DARK if theme == "dark" else CSS_LIGHT
    st.markdown(f"<style>{CSS_COMMON}{css}</style>", unsafe_allow_html=True)
