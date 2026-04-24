"""
PayGlobal AI Assistant — Streamlit entrypoint.

This file intentionally stays small and delegates to UI + service modules.
"""

import streamlit as st

from auth import bootstrap_admin, login, register
from config import APP_TITLE, GROK_API_KEY, PAYGLOBAL_MODULES, RATE_LIMIT_PER_HOUR, UPLOADS_DIR
from db import (
    delete_conversation,
    delete_user,
    get_all_conversations_admin,
    get_all_users,
    get_analytics_data,
    get_recent_audit_log,
    get_user_conversations,
    reset_user_password,
    save_feedback,
    update_user_role,
)
from ingest import ingest_file
from services.chat_service import (
    auto_title as auto_title_service,
    handle_message as handle_message_service,
    load_chain as load_chain_service,
    load_conversation as load_conversation_service,
    start_new_conversation as start_new_conversation_service,
)
from services.state import init_state as init_app_state
from ui.admin_view import render_admin_panel
from ui.analytics_view import render_analytics
from ui.auth_view import render_login_page
from ui.chat_view import render_chat
from ui.sidebar_view import render_sidebar
from ui.theme import apply_theme as apply_enterprise_theme
from utils.exporter import export_answer_pdf, export_to_docx, export_to_pdf


st.set_page_config(
    page_title="PayGlobal AI Assistant",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


bootstrap_admin()
init_app_state(GROK_API_KEY)
apply_enterprise_theme()


def load_chain() -> None:
    load_chain_service()


def start_new_conversation() -> None:
    start_new_conversation_service()


def load_conversation(conv_id: int) -> None:
    load_conversation_service(conv_id)


def auto_title(conv_id: int, first_user_msg: str) -> None:
    auto_title_service(conv_id, first_user_msg)


def _handle_message(user_input: str) -> None:
    handle_message_service(user_input)


def show_login_page() -> None:
    render_login_page(login_fn=login, register_fn=register, default_api_key=GROK_API_KEY)


def show_sidebar() -> None:
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


def show_chat() -> None:
    render_chat(
        app_title=APP_TITLE,
        save_feedback_fn=save_feedback,
        export_answer_pdf_fn=export_answer_pdf,
        start_new_conversation_fn=start_new_conversation,
        handle_message_fn=_handle_message,
    )


def show_analytics() -> None:
    render_analytics(get_analytics_data_fn=get_analytics_data, get_all_users_fn=get_all_users)


def show_admin_panel() -> None:
    render_admin_panel(
        uploads_dir=UPLOADS_DIR,
        rate_limit_per_hour=RATE_LIMIT_PER_HOUR,
        get_analytics_data_fn=get_analytics_data,
        get_all_users_fn=get_all_users,
        update_user_role_fn=update_user_role,
        reset_user_password_fn=reset_user_password,
        delete_user_fn=delete_user,
        get_recent_audit_log_fn=get_recent_audit_log,
    )


def show_admin_quick_nav() -> None:
    """Fallback nav visible in main area even if sidebar is collapsed."""
    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Chat", key="top_nav_chat", width="stretch", type="primary" if st.session_state.page == "chat" else "secondary"):
            st.session_state.page = "chat"
            st.rerun()
    with c2:
        if st.button("Stats", key="top_nav_stats", width="stretch", type="primary" if st.session_state.page == "analytics" else "secondary"):
            st.session_state.page = "analytics"
            st.rerun()
    with c3:
        if st.button("Admin", key="top_nav_admin", width="stretch", type="primary" if st.session_state.page == "admin" else "secondary"):
            st.session_state.page = "admin"
            st.rerun()


if not st.session_state.authenticated:
    show_login_page()
else:
    try:
        show_sidebar()
        show_admin_quick_nav()
        if st.session_state.page == "analytics":
            show_analytics()
        elif st.session_state.page == "admin":
            show_admin_panel()
        else:
            show_chat()
    except Exception as exc:
        st.error("A page rendering error occurred. Returning to Chat is recommended.")
        st.exception(exc)
        if st.button("Return to Chat", key="recover_to_chat", type="primary", width="stretch"):
            st.session_state.page = "chat"
            st.rerun()

