import time

import streamlit as st


def init_state(default_api_key: str) -> None:
    defaults = {
        "authenticated": False,
        "user": None,
        "conv_id": None,
        "messages": [],
        "rag_chain": None,
        "module": "All Modules",
        "filter_year": "",
        "filter_version": "",
        "filter_customer": "",
        "show_login": True,
        "api_key": default_api_key,
        "page": "chat",
        "admin_view_all": False,
        "theme": "dark",
        "last_activity_ts": time.time(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
