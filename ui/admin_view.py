from datetime import datetime
import json
from pathlib import Path

import streamlit as st

from auth import hash_password, register as auth_register
from config import GROK_BASE_URL, GROK_MODEL, SYSTEM_PROMPT_PATH
from ingest import ingest_file, index_exists


def render_admin_panel(
    *,
    uploads_dir,
    rate_limit_per_hour: int,
    get_analytics_data_fn,
    get_all_users_fn,
    update_user_role_fn,
    reset_user_password_fn,
    delete_user_fn,
    get_recent_audit_log_fn,
) -> None:
    user = st.session_state.user
    if user["role"] != "admin":
        st.error("⛔ Access denied. Admin only.")
        return

    st.markdown(
        """
    <div class='topbar'>
        <span class='topbar-title'>⚙️ Admin Control Panel</span>
        <span class='topbar-user'>Full backend control · Admin only</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🏥 System Health", "👤 User Management", "📚 Knowledge Base", "⚙️ Model Config", "✏️ Prompt Editor", "📋 Audit Log"])

    with tabs[0]:
        idx_ok = index_exists()
        st.markdown("#### 🔍 Live Status")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Vector Index", "✅ Ready" if idx_ok else "❌ Missing")
        sc2.metric("LLM Model", GROK_MODEL.split("/")[-1])
        sc3.metric("API Provider", "Groq (free)" if "groq" in GROK_BASE_URL else "xAI")

        faiss_chunks = 0
        if idx_ok:
            try:
                manifest_path = uploads_dir.parent / "ingested_manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if isinstance(manifest, dict):
                        faiss_chunks = sum(int(item.get("chunks", 0) or 0) for item in manifest.values() if isinstance(item, dict))
            except Exception:
                # Keep panel responsive even if manifest parsing fails.
                faiss_chunks = 0
        sc4.metric("Indexed Chunks", faiss_chunks)

        st.divider()
        data = get_analytics_data_fn()
        st.markdown("#### 📊 Database Totals")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Users", data["total_users"])
        d2.metric("Conversations", data["total_conversations"])
        d3.metric("Messages", data["total_messages"])
        d4.metric("User Questions", data["total_questions"])

        st.divider()
        fb = data.get("feedback", {})
        if fb.get("total", 0):
            up, dn = fb.get("thumbs_up", 0) or 0, fb.get("thumbs_down", 0) or 0
            pct = round(up / fb["total"] * 100)
            st.markdown(
                f"**Feedback satisfaction:** 👍 {up} &nbsp;|&nbsp; 👎 {dn} &nbsp;→&nbsp; "
                f"<span style='color:#10b981;font-weight:700;'>{pct}% positive</span>",
                unsafe_allow_html=True,
            )
        st.info(f"⏱️ Rate limit: **{rate_limit_per_hour} req/hr** per user. Admins are always exempt.")

    with tabs[1]:
        st.markdown("#### 👥 Registered Users")
        all_users = get_all_users_fn()
        for item in all_users:
            is_me = item["id"] == user["id"]
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2.2, 2.5, 1.5, 2.8, 0.8])
                badge = "🔵" if item["role"] == "admin" else "⚪"
                c1.markdown(f"{badge} **{item['username']}** {'*(you)*' if is_me else ''}")
                c2.markdown(f"`{item.get('email') or '—'}`")

                with c3:
                    if not is_me:
                        sel = st.selectbox("Role", ["user", "admin"], index=0 if item["role"] == "user" else 1, key=f"rsel_{item['id']}", label_visibility="collapsed")
                        if sel != item["role"]:
                            update_user_role_fn(item["id"], sel)
                            st.toast(f"✅ {item['username']} → {sel}")
                            st.rerun()
                    else:
                        st.caption(f"`{item['role']}`")

                with c4:
                    if not is_me:
                        new_pw = st.text_input("New password", key=f"npw_{item['id']}", placeholder="New password…", type="password", label_visibility="collapsed")
                        if st.button("🔑 Reset", key=f"rpw_{item['id']}", width="stretch"):
                            if new_pw and len(new_pw) >= 6:
                                reset_user_password_fn(item["id"], hash_password(new_pw))
                                st.toast(f"🔑 Password reset for {item['username']}")
                            else:
                                st.warning("Min 6 characters required.")

                with c5:
                    if not is_me and st.button("🗑️", key=f"delu_{item['id']}", help=f"Delete {item['username']}"):
                        delete_user_fn(item["id"])
                        st.toast(f"🗑️ Deleted {item['username']}")
                        st.rerun()
            st.divider()

        st.markdown("#### ➕ Create New User")
        with st.form("admin_create_user", clear_on_submit=True):
            nu1, nu2 = st.columns(2)
            with nu1:
                nu_user = st.text_input("Username", placeholder="Enter username")
                nu_email = st.text_input("Email", placeholder="user@company.com")
            with nu2:
                nu_pw = st.text_input("Password", placeholder="Min 8 chars", type="password")
                nu_role = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("➕ Create User", type="primary"):
                if nu_user and nu_pw and len(nu_pw) >= 8:
                    try:
                        auth_register(nu_user, nu_pw, nu_email, nu_role)
                        st.success(f"✅ User **{nu_user}** created as `{nu_role}`")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                else:
                    st.error("Username required and password must be ≥ 8 characters.")

    with tabs[2]:
        st.markdown("#### 📂 Uploaded Files")
        files = sorted(uploads_dir.glob("*.*"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            st.info("No documents uploaded yet. Use the sidebar to upload PDFs/DOCX.")
        else:
            for file in files:
                size_kb = file.stat().st_size / 1024
                ts = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                fc1, fc2, fc3, fc4 = st.columns([3, 1.2, 1.5, 0.8])
                fc1.markdown(f"📄 `{file.name}`")
                fc2.markdown(f"`{size_kb:.1f} KB`")
                fc3.markdown(f"`{ts}`")
                with fc4:
                    if st.button("🗑️", key=f"delf_{file.name}", help=f"Delete {file.name}"):
                        file.unlink()
                        st.toast(f"Deleted {file.name}")
                        st.rerun()
                st.divider()

        st.markdown("#### ♻️ Re-index All Documents")
        st.caption("Wipes and rebuilds the entire FAISS vector store from all uploaded files.")
        if st.button("⚡ Re-ingest Everything", type="primary", width="stretch"):
            if files:
                total_chunks, prog = 0, st.progress(0)
                for i, file in enumerate(files):
                    try:
                        total_chunks += ingest_file(file)
                    except Exception as exc:
                        st.warning(f"⚠️ {file.name}: {exc}")
                    prog.progress((i + 1) / len(files))
                st.session_state.rag_chain = None
                st.success(f"✅ Re-indexed {len(files)} file(s) → {total_chunks} chunks")
            else:
                st.warning("No files to ingest.")

    with tabs[3]:
        st.markdown("#### 🤖 LLM & Rate Limit Configuration")
        groq_models = [
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "groq/compound",
            "groq/compound-mini",
        ]
        mc1, mc2 = st.columns([3, 2])
        with mc1:
            cur_idx = groq_models.index(GROK_MODEL) if GROK_MODEL in groq_models else 0
            new_model = st.selectbox("LLM Model", groq_models, index=cur_idx)
            new_url = st.text_input("API Base URL", value=GROK_BASE_URL)
            new_rate = st.number_input("Rate limit (req/hr per user)", min_value=5, max_value=500, value=int(rate_limit_per_hour), step=5)
        with mc2:
            st.markdown("**Free models on Groq:**")
            for model in groq_models:
                active = "✅ " if model == GROK_MODEL else "· "
                st.markdown(f"{active}`{model}`")

        if st.button("💾 Apply Config", type="primary", width="stretch"):
            env_path = Path(__file__).resolve().parents[1] / ".env"
            lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
            env_dict = {}
            for line in lines:
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env_dict[k.strip()] = v.strip()
            env_dict["GROK_MODEL"] = new_model
            env_dict["GROK_BASE_URL"] = new_url
            env_dict["RATE_LIMIT_PER_HOUR"] = str(int(new_rate))
            env_path.write_text("\n".join(f"{k}={v}" for k, v in env_dict.items()) + "\n", encoding="utf-8")
            st.session_state.rag_chain = None
            st.success(f"✅ Saved! Model: **{new_model}** · Rate: **{int(new_rate)}/hr**\n\n⚠️ Restart the app for model/URL changes to fully take effect.")

    with tabs[4]:
        st.markdown("#### ✏️ System Prompt Editor")
        st.caption("Defines the AI's scope, tone, and response style. Saved changes take effect on next question.")
        current_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else ""
        new_prompt = st.text_area("System prompt", value=current_prompt, height=380, label_visibility="collapsed", placeholder="You are a helpful PayGlobal AI assistant…")
        pe1, pe2 = st.columns(2)
        with pe1:
            if st.button("💾 Save Prompt", type="primary", width="stretch"):
                SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SYSTEM_PROMPT_PATH.write_text(new_prompt, encoding="utf-8")
                st.session_state.rag_chain = None
                st.success("✅ Prompt saved. AI will use it on the next question.")
        with pe2:
            if st.button("↩️ Reset to Default", width="stretch"):
                default = (
                    "You are PayGlobal Expert, an AI consultant specialising exclusively in the PayGlobal ERP system.\n\n"
                    "Use the provided context to answer questions about PayGlobal installation, "
                    "configuration, troubleshooting, and functionality.\n\n"
                    "Context:\n{context}\n\n"
                    "Rules:\n"
                    "- Only answer questions related to PayGlobal\n"
                    "- Be precise, structured, and professional\n"
                    "- Use markdown formatting (headers, bullet points, tables) for clarity\n"
                    "- Cite page numbers when available"
                )
                SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SYSTEM_PROMPT_PATH.write_text(default, encoding="utf-8")
                st.session_state.rag_chain = None
                st.success("✅ Reset to default prompt.")
                st.rerun()

    with tabs[5]:
        import pandas as pd

        st.markdown("#### 📋 Recent User Queries")
        logs = get_recent_audit_log_fn(100)
        if not logs:
            st.info("No activity logged yet.")
        else:
            df = pd.DataFrame(logs)
            expected_cols = ["username", "conversation", "module", "role", "content", "timestamp"]
            for col in expected_cols:
                if col not in df.columns:
                    df[col] = ""
            df = df[expected_cols]
            df.columns = ["User", "Conversation", "Module", "Role", "Question", "Timestamp"]
            df["Timestamp"] = df["Timestamp"].astype(str).str[:16]
            df["Question"] = df["Question"].astype(str).str[:120] + "…"
            df.index = df.index + 1
            st.dataframe(df[["Timestamp", "User", "Module", "Question"]], width="stretch", height=460)
