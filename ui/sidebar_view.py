from datetime import datetime
from html import escape

import streamlit as st


def render_sidebar(
    *,
    modules,
    uploads_dir,
    ingest_file_fn,
    export_to_pdf_fn,
    export_to_docx_fn,
    get_analytics_data_fn,
    get_all_conversations_admin_fn,
    get_user_conversations_fn,
    delete_conversation_fn,
    start_new_conversation_fn,
    load_conversation_fn,
) -> None:
    with st.sidebar:
        user = st.session_state.user
        is_admin = user["role"] == "admin"
        is_dark = st.session_state.get("theme", "dark") == "dark"

        hc1, hc2 = st.columns([5, 1])
        with hc1:
            st.markdown(
                "<div style='display:flex;align-items:center;padding:.3rem 0;'>"
                "<span style='font-size:1rem;font-weight:700;color:#4f6ef7;'>PG</span>"
                "<div style='margin-left:.5rem;'>"
                "<div style='font-size:.85rem;font-weight:700;'>PayGlobal AI</div>"
                "<div style='font-size:.6rem;color:#6b7a99;'>Enterprise Assistant</div>"
                "</div></div>",
                unsafe_allow_html=True,
            )
        with hc2:
            if st.button("☀️" if is_dark else "🌙", key="theme_toggle", help="Toggle light/dark mode"):
                st.session_state.theme = "light" if is_dark else "dark"
                st.rerun()

        badge_color = "#4f6ef7" if is_admin else "#10b981"
        safe_username = escape(user["username"])
        safe_role = escape(user["role"])
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:.4rem;"
            f"padding:.3rem 0 .5rem;border-bottom:1px solid rgba(48,54,61,0.3);margin-bottom:.4rem;'>"
            f"<span style='font-size:.72rem;color:#8b949e;'>👤 {safe_username}</span>"
            f"<span style='font-size:.6rem;font-weight:600;padding:.08rem .35rem;"
            f"border-radius:999px;background:rgba(79,110,247,.15);color:{badge_color};'>"
            f"{safe_role}</span></div>",
            unsafe_allow_html=True,
        )

        if is_admin:
            page = st.session_state.page
            n1, n2, n3 = st.columns(3)
            with n1:
                if st.button("💬 Chat", key="nav_chat", width="stretch", type="primary" if page == "chat" else "secondary"):
                    st.session_state.page = "chat"
                    st.rerun()
            with n2:
                if st.button(
                    "📊 Stats",
                    key="nav_analytics",
                    width="stretch",
                    type="primary" if page == "analytics" else "secondary",
                ):
                    st.session_state.page = "analytics"
                    st.rerun()
            with n3:
                if st.button("⚙️ Admin", key="nav_admin", width="stretch", type="primary" if page == "admin" else "secondary"):
                    st.session_state.page = "admin"
                    st.rerun()
            st.markdown("<div style='height:.15rem'></div>", unsafe_allow_html=True)

        if st.button("＋  New Chat", key="new_chat_btn", width="stretch"):
            start_new_conversation_fn()
            st.rerun()

        st.markdown("<div class='sb-section-label'>Module</div>", unsafe_allow_html=True)
        module = st.selectbox(
            "Module filter",
            modules,
            index=modules.index(st.session_state.module),
            label_visibility="collapsed",
        )
        if module != st.session_state.module:
            st.session_state.module = module

        st.markdown("<div class='sb-section-label'>Filters</div>", unsafe_allow_html=True)
        fy = st.text_input(
            "Year",
            value=st.session_state.get("filter_year", ""),
            placeholder="e.g. 2025",
            label_visibility="collapsed",
            key="filter_year_input",
        )
        fv = st.text_input(
            "Version",
            value=st.session_state.get("filter_version", ""),
            placeholder="e.g. v10 / 10.2",
            label_visibility="collapsed",
            key="filter_version_input",
        )
        fc = st.text_input(
            "Customer",
            value=st.session_state.get("filter_customer", ""),
            placeholder="e.g. Acme",
            label_visibility="collapsed",
            key="filter_customer_input",
        )
        if fy != st.session_state.get("filter_year", ""):
            st.session_state.filter_year = fy.strip()
            st.session_state.rag_chain = None
        if fv != st.session_state.get("filter_version", ""):
            st.session_state.filter_version = fv.strip()
            st.session_state.rag_chain = None
        if fc != st.session_state.get("filter_customer", ""):
            st.session_state.filter_customer = fc.strip()
            st.session_state.rag_chain = None

        if is_admin:
            st.markdown("<div class='sb-section-label'>API Key</div>", unsafe_allow_html=True)
            kc1, kc2 = st.columns([5, 1])
            with kc1:
                api_key_input = st.text_input(
                    "API Key",
                    value=st.session_state.api_key,
                    type="password",
                    label_visibility="collapsed",
                    placeholder="gsk_… or xai-…",
                )
            with kc2:
                test_key = st.button("✓", help="Test API connection", width="stretch")

            if api_key_input != st.session_state.api_key:
                st.session_state.api_key = api_key_input
                st.session_state.rag_chain = None

            if test_key:
                if not api_key_input:
                    st.warning("Enter a key first.")
                else:
                    with st.spinner("Testing…"):
                        try:
                            import requests as _rq

                            from config import GROK_BASE_URL

                            response = _rq.post(
                                GROK_BASE_URL.rstrip("/") + "/chat/completions",
                                headers={"Authorization": f"Bearer {api_key_input}", "Content-Type": "application/json"},
                                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                                timeout=8,
                            )
                            st.success("✅ Connected") if response.status_code in (200, 201) else st.warning("⚠️ No credits") if "credits" in response.text.lower() else st.error(f"❌ {response.status_code}")
                        except Exception as exc:
                            st.error(f"❌ {exc}")

        st.markdown("<div class='sb-section-label'>Conversations</div>", unsafe_allow_html=True)
        if is_admin:
            try:
                data = get_analytics_data_fn()
                st.markdown(
                    f"<div style='font-size:.63rem;color:#4f6ef7;margin-bottom:.3rem;'>"
                    f"👥 {data['total_users']} users &nbsp;·&nbsp; "
                    f"💬 {data['total_conversations']} convs &nbsp;·&nbsp; "
                    f"❓ {data['total_questions']} queries</div>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass
            label = "Viewing: All Users" if st.session_state.admin_view_all else "Viewing: My Chats"
            if st.button(label, key="admin_toggle", width="stretch"):
                st.session_state.admin_view_all = not st.session_state.admin_view_all
                st.rerun()

        conversations = get_all_conversations_admin_fn() if (is_admin and st.session_state.admin_view_all) else get_user_conversations_fn(user["id"])

        search_q = st.text_input("Search conversations", placeholder="🔍 Search…", label_visibility="collapsed", key="conv_search")
        if search_q:
            conversations = [c for c in conversations if search_q.lower() in (c.get("title") or "").lower()]

        if not conversations:
            st.caption("No conversations yet." if not search_q else "No matches found.")

        for conv in conversations:
            c1, c2 = st.columns([6, 1])
            with c1:
                prefix = f"[{conv.get('username', '?')}] " if (is_admin and st.session_state.admin_view_all) else ""
                title = (prefix + (conv["title"] or "New Chat"))[:40]
                active = conv["id"] == st.session_state.conv_id
                if st.button(("▶ " if active else "") + title, key=f"conv_{conv['id']}", width="stretch"):
                    load_conversation_fn(conv["id"])
                    st.session_state.page = "chat"
                    st.rerun()
            with c2:
                if st.button("×", key=f"del_{conv['id']}"):
                    delete_conversation_fn(conv["id"])
                    if st.session_state.conv_id == conv["id"]:
                        st.session_state.conv_id = None
                        st.session_state.messages = []
                        st.session_state.rag_chain = None
                    st.rerun()

        with st.expander("📄 Documents & Export"):
            uploaded_files = st.file_uploader("Upload documents", type=["pdf", "docx"], accept_multiple_files=True, label_visibility="collapsed")
            if uploaded_files and st.button("⚡ Ingest", width="stretch", type="primary"):
                total_chunks = 0
                with st.spinner("Ingesting…"):
                    for uploaded in uploaded_files:
                        save_path = uploads_dir / uploaded.name
                        save_path.write_bytes(uploaded.getbuffer())
                        try:
                            total_chunks += ingest_file_fn(save_path)
                        except Exception as exc:
                            st.error(f"{uploaded.name}: {exc}")
                st.success(f"✅ {len(uploaded_files)} file(s) → {total_chunks} chunks")
                st.session_state.rag_chain = None

            messages = st.session_state.get("messages", [])
            if messages:
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                try:
                    st.download_button(
                        "⬇️ Download PDF",
                        data=export_to_pdf_fn(messages, user["username"], st.session_state.module),
                        file_name=f"chat_{ts}.pdf",
                        mime="application/pdf",
                        width="stretch",
                        key="dl_pdf",
                    )
                except Exception:
                    pass
                try:
                    st.download_button(
                        "⬇️ Download Word",
                        data=export_to_docx_fn(messages, user["username"], st.session_state.module),
                        file_name=f"chat_{ts}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch",
                        key="dl_docx",
                    )
                except Exception:
                    pass

        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        if st.button("⎋  Sign Out", key="signout_btn", width="stretch"):
            try:
                st.query_params.clear()
            except Exception:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
