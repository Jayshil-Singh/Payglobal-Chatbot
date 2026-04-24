import streamlit as st


def render_login_page(login_fn, register_fn, default_api_key: str) -> None:
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            """
        <div style='text-align:center; margin-top:3rem; margin-bottom:2rem;'>
            <div style='font-size:2.2rem;font-weight:700;color:#4f6ef7;'>PG</div>
            <h1 style='color:#e6edf3; font-size:1.9rem; font-weight:700; margin:0.3rem 0;'>
                PayGlobal AI Assistant
            </h1>
            <p style='color:#8b949e; font-size:0.9rem;'>
                Enterprise support copilot for implementation teams
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = login_fn(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.api_key = default_api_key
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_register:
            with st.form("reg_form"):
                new_user = st.text_input("Username", placeholder="Choose a username")
                new_email = st.text_input("Email (optional)", placeholder="your@email.com")
                new_pass = st.text_input("Password", type="password", placeholder="Min 8 characters")
                new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
                reg_btn = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if reg_btn:
                if new_pass != new_pass2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        user = register_fn(new_user, new_pass, new_email)
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success("Account created! Welcome aboard")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
