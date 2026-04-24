import streamlit as st


def render_analytics(get_analytics_data_fn, get_all_users_fn) -> None:
    """Render admin analytics dashboard."""
    user = st.session_state.user
    if user["role"] != "admin":
        st.error("⛔ Access denied. Admin only.")
        return
    is_dark = st.session_state.get("theme", "dark") == "dark"

    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    st.markdown(
        """
    <div class='topbar'>
        <span class='topbar-title'>📊 Analytics Dashboard</span>
        <span class='topbar-user'>Admin view · Real-time data</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.spinner("Loading analytics…"):
        data = get_analytics_data_fn()

    k1, k2, k3, k4 = st.columns(4)
    kpi_style = (
        "background:#0d1117; border:1px solid rgba(48,54,61,0.8); border-radius:12px; padding:1.2rem; text-align:center;"
        if is_dark
        else "background:#ffffff; border:1px solid rgba(180,193,218,0.8); border-radius:12px; padding:1.2rem; text-align:center; box-shadow:0 2px 8px rgba(79,110,247,0.08);"
    )
    text_muted = "#8b949e" if is_dark else "#64748b"
    chart_bg = "#0d1117" if is_dark else "#ffffff"
    chart_font = "#e6edf3" if is_dark else "#1e293b"
    chart_grid = "rgba(48,54,61,0.5)" if is_dark else "rgba(203,213,225,0.8)"

    def kpi(col, icon, label, value, color="#4f6ef7"):
        col.markdown(
            f"""
        <div style='{kpi_style}'>
            <div style='font-size:1.8rem;'>{icon}</div>
            <div style='font-size:2rem; font-weight:700; color:{color};'>{value}</div>
            <div style='font-size:0.78rem; color:#8b949e; margin-top:0.2rem;'>{label}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    kpi(k1, "👥", "Total Users", data["total_users"], "#4f6ef7")
    kpi(k2, "💬", "Conversations", data["total_conversations"], "#10b981")
    kpi(k3, "📨", "Total Messages", data["total_messages"], "#f59e0b")
    kpi(k4, "❓", "User Questions", data["total_questions"], "#ef4444")

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_pie = st.columns([3, 2])
    with col_chart:
        st.markdown("#### 📅 Questions per Day (Last 14 Days)")
        daily = data.get("daily_messages", [])
        if daily:
            days = [d["day"] for d in daily]
            cnts = [d["cnt"] for d in daily]
            fig = go.Figure(go.Bar(x=days, y=cnts, marker_color="#4f6ef7", marker_line_color="rgba(79,110,247,0.3)", marker_line_width=1))
            fig.update_layout(
                paper_bgcolor=chart_bg,
                plot_bgcolor=chart_bg,
                font=dict(color=chart_font, size=11),
                xaxis=dict(gridcolor=chart_grid, tickangle=-35),
                yaxis=dict(gridcolor=chart_grid),
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No activity data yet.")

    with col_pie:
        st.markdown("#### 📦 Module Usage")
        modules = data.get("module_usage", [])
        if modules:
            labels = [m["module"] for m in modules]
            values = [m["cnt"] for m in modules]
            fig2 = go.Figure(go.Pie(labels=labels, values=values, hole=0.45, marker=dict(colors=px.colors.qualitative.Plotly), textfont=dict(size=11)))
            fig2.update_layout(
                paper_bgcolor=chart_bg,
                font=dict(color=chart_font, size=11),
                margin=dict(l=0, r=0, t=10, b=0),
                height=280,
                showlegend=True,
                legend=dict(bgcolor=chart_bg, font=dict(size=10, color=chart_font)),
            )
            st.plotly_chart(fig2, width="stretch")
        else:
            st.info("No module data yet.")

    col_fb, col_users = st.columns([1, 2])
    with col_fb:
        st.markdown("#### 👍 Feedback Satisfaction")
        fb = data.get("feedback", {})
        total_fb = fb.get("total", 0)
        up = fb.get("thumbs_up", 0) or 0
        dn = fb.get("thumbs_down", 0) or 0
        if total_fb:
            pct = round(up / total_fb * 100)
            fig3 = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    number={"suffix": "%", "font": {"color": chart_font, "size": 32}},
                    gauge={
                        "axis": {"range": [0, 100], "tickcolor": text_muted},
                        "bar": {"color": "#10b981"},
                        "bgcolor": "#161b27" if is_dark else "#eef2ff",
                        "steps": [
                            {"range": [0, 50], "color": "rgba(239,68,68,0.15)"},
                            {"range": [50, 75], "color": "rgba(245,158,11,0.15)"},
                            {"range": [75, 100], "color": "rgba(16,185,129,0.15)"},
                        ],
                    },
                )
            )
            fig3.update_layout(paper_bgcolor=chart_bg, font=dict(color=chart_font), margin=dict(l=10, r=10, t=20, b=10), height=220)
            st.plotly_chart(fig3, width="stretch")
            st.markdown(
                f"<div style='text-align:center; font-size:0.8rem; color:{text_muted};'>👍 {up} &nbsp;|&nbsp; 👎 {dn} &nbsp;|&nbsp; Total {total_fb}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("No feedback yet.")

    with col_users:
        st.markdown("#### 🏆 Most Active Users")
        top_users = data.get("top_users", [])
        if top_users:
            df = pd.DataFrame(top_users)
            df.columns = ["Username", "Questions Asked"]
            df.index = df.index + 1
            st.dataframe(df, width="stretch", height=230)
        else:
            st.info("No user activity yet.")

    st.divider()
    st.markdown("#### 👤 Registered Users")
    all_users = get_all_users_fn()
    if all_users:
        udf = pd.DataFrame(all_users)
        expected_cols = ["username", "email", "role", "created_at", "last_login"]
        for col in expected_cols:
            if col not in udf.columns:
                udf[col] = ""
        udf = udf[expected_cols]
        udf.columns = ["Username", "Email", "Role", "Registered", "Last Login"]
        udf.index = udf.index + 1
        st.dataframe(udf, width="stretch")
    else:
        st.info("No users found.")
