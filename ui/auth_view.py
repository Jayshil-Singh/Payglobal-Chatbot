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

        # Enterprise mode: no self-registration. Admins provision users in Admin panel.
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

        st.caption("No self-registration. Ask an admin to create your account.")
