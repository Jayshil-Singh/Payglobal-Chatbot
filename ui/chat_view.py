import streamlit as st


def render_chat(*, app_title: str, save_feedback_fn, export_answer_pdf_fn, start_new_conversation_fn, handle_message_fn) -> None:
    user = st.session_state.user
    is_admin = user["role"] == "admin"

    if "api_status" not in st.session_state:
        st.session_state.api_status = "unknown"

    if is_admin and st.session_state.api_key:
        if st.session_state.get("_last_status_check") != st.session_state.api_key[:8]:
            try:
                import requests as _rq
                from config import GROK_BASE_URL, GROK_MODEL

                r = _rq.post(
                    GROK_BASE_URL.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {st.session_state.api_key}", "Content-Type": "application/json"},
                    json={"model": GROK_MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                    timeout=5,
                )
                st.session_state.api_status = "green" if r.status_code in (200, 201) else "amber" if "credits" in r.text.lower() else "red"
            except Exception:
                st.session_state.api_status = "red"
            st.session_state._last_status_check = st.session_state.api_key[:8]

    from config import GROK_MODEL as _MDL

    module = st.session_state.module
    if is_admin:
        sdot = st.session_state.api_status
        slbl = {"green": "AI Online", "amber": "No Credits", "red": "Offline", "unknown": "Connecting…"}.get(sdot, "")
        scol = {"green": "#10b981", "amber": "#f59e0b", "red": "#ef4444", "unknown": "#4b5563"}.get(sdot, "#4b5563")
        status = (
            "<span style='display:inline-flex;align-items:center;gap:.35rem;'>"
            f"<span style='width:7px;height:7px;border-radius:50%;background:{scol};display:inline-block;box-shadow:0 0 5px {scol};'></span>"
            f"<span style='font-size:.72rem;color:#6b7a99;'>{slbl}</span></span>"
        )
        model_lbl = _MDL.split("/")[-1]
        model = f"<span style='font-size:.65rem;color:#3d4a5c;padding:.1rem .4rem;border:1px solid rgba(48,54,61,0.45);border-radius:5px;'>{model_lbl}</span>"
    else:
        status = ""
        model = ""

    module_html = f"<span style='font-size:.76rem;'>Module: <b style='color:#4f6ef7;'>{module}</b></span>"

    st.markdown(
        "<div class='topbar'>"
        f"<span class='topbar-title'>🌐 {app_title}</span>"
        "<span class='topbar-user' style='display:flex;align-items:center;gap:.8rem;'>"
        f"{status}{module_html}{model}"
        "</span></div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.conv_id:
        start_new_conversation_fn()

    messages = st.session_state.messages
    if not messages:
        st.markdown(
            """
        <div style='text-align:center; padding:4rem 2rem; color:#8b949e;'>
            <div style='font-size:3rem; margin-bottom:1rem;'>💬</div>
            <h3 style='color:#e6edf3; margin-bottom:0.5rem;'>Ask me anything about PayGlobal</h3>
            <p style='font-size:0.9rem;'>Installation &middot; Configuration &middot; Troubleshooting &middot; Functional Guidance</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        example_prompts = [
            "How do I install the PayGlobal Payroll module?",
            "Configure ESS portal step by step",
            "Fix database connection error during setup",
            "Setup employee master data",
        ]
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

                if msg["role"] == "assistant" and msg.get("msg_id"):
                    msg_id = msg["msg_id"]
                    col_up, col_dn, col_pdf, _ = st.columns([1, 1, 2, 6])
                    with col_up:
                        if st.button("👍", key=f"up_{msg_id}_{idx}", help="Good answer"):
                            save_feedback_fn(msg_id, st.session_state.user["id"], 1)
                            st.toast("Thanks for your feedback!", icon="👍")
                    with col_dn:
                        if st.button("👎", key=f"dn_{msg_id}_{idx}", help="Bad answer"):
                            save_feedback_fn(msg_id, st.session_state.user["id"], -1)
                            st.toast("Feedback recorded — we'll improve!", icon="👎")
                    with col_pdf:
                        try:
                            ans_pdf = export_answer_pdf_fn(msg["content"], msg.get("sources", []), st.session_state.user["username"])
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

    pending = st.session_state.pop("_pending_prompt", None)
    user_input = st.chat_input("Ask about PayGlobal implementation, configuration, or troubleshooting...") or pending
    if user_input:
        handle_message_fn(user_input)

