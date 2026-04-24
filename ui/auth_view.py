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
            submitted = st.form_submit_button("Sign In", width="stretch", type="primary")

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


def render_force_password_change(set_new_password_fn) -> None:
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            """
        <div style='text-align:center; margin-top:2.5rem; margin-bottom:1.2rem;'>
            <h2 style='margin:.2rem 0;'>Change Temporary Password</h2>
            <p style='color:#8b949e; font-size:.9rem;'>For security, you must set a new password before continuing.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        with st.form("force_pw_change"):
            new_pw = st.text_input("New Password", type="password", placeholder="At least 8 characters")
            confirm_pw = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            submitted = st.form_submit_button("Update Password", width="stretch", type="primary")

        if submitted:
            if not new_pw or not confirm_pw:
                st.error("Please fill in both fields.")
                return
            if new_pw != confirm_pw:
                st.error("Passwords do not match.")
                return
            if len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
                return
            set_new_password_fn(st.session_state.user["id"], new_pw, False)
            st.session_state.user["must_change_password"] = 0
            st.success("Password updated successfully. Please continue.")
            st.rerun()
