import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from auth import generate_temp_password, hash_password, set_new_password, validate_password_strength
from auth import register as auth_register
from config import DATA_RETENTION_DAYS, GROK_BASE_URL, GROK_MODEL, SYSTEM_PROMPT_PATH
from ingest import index_exists, ingest_file
from utils.mailer import send_email


def render_admin_panel(
    *,
    uploads_dir,
    rate_limit_per_hour: int,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sendgrid_api_key: str,
    sendgrid_from_email: str,
    get_analytics_data_fn,
    get_all_users_fn,
    update_user_role_fn,
    reset_user_password_fn,
    set_user_active_fn,
    unlock_user_fn,
    add_admin_audit_event_fn,
    get_admin_audit_events_fn,
    delete_user_fn,
    get_recent_audit_log_fn,
    purge_data_older_than_fn=None,
    ingest_folder_fn=None,
    raw_docs_dir=None,
) -> None:
    user = st.session_state.user
    is_dark = st.session_state.get("theme", "dark") == "dark"
    if user["role"] != "admin":
        st.error("⛔ Access denied. Admin only.")
        return

    card_bg = "#0d1117" if is_dark else "#ffffff"
    card_border = "rgba(48,54,61,0.8)" if is_dark else "rgba(180,193,218,0.85)"
    label_color = "#8b949e" if is_dark else "#64748b"
    value_color = "#e6edf3" if is_dark else "#0f172a"

    def render_stat_card(col, label: str, value: str) -> None:
        col.markdown(
            f"""
            <div style="
                background:{card_bg};
                border:1px solid {card_border};
                border-radius:12px;
                padding:.7rem .8rem;
                min-height:88px;
            ">
                <div style="font-size:.73rem;color:{label_color};margin-bottom:.35rem;">{label}</div>
                <div style="font-size:2rem;line-height:1.05;font-weight:700;color:{value_color};">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
        render_stat_card(sc1, "Vector Index", "✅ Ready" if idx_ok else "❌ Missing")
        render_stat_card(sc2, "LLM Model", GROK_MODEL.split("/")[-1])
        render_stat_card(sc3, "API Provider", "Groq (free)" if "groq" in GROK_BASE_URL else "xAI")

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
        render_stat_card(sc4, "Indexed Chunks", str(faiss_chunks))

        st.divider()
        data = get_analytics_data_fn()
        st.markdown("#### 📊 Database Totals")
        d1, d2, d3, d4 = st.columns(4)
        render_stat_card(d1, "Users", str(data["total_users"]))
        render_stat_card(d2, "Conversations", str(data["total_conversations"]))
        render_stat_card(d3, "Messages", str(data["total_messages"]))
        render_stat_card(d4, "User Questions", str(data["total_questions"]))

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

        if purge_data_older_than_fn:
            st.divider()
            st.markdown("#### 🧹 Data Retention")
            days = st.number_input(
                "Retention (days)",
                min_value=7,
                max_value=3650,
                value=int(DATA_RETENTION_DAYS),
                step=7,
            )
            if st.button("Purge old data now", type="primary", width="stretch"):
                res = purge_data_older_than_fn(int(days))
                st.success(
                    f"Purged: {res.get('deleted_messages', 0)} messages, {res.get('deleted_conversations', 0)} conversations."
                )

    with tabs[1]:
        import pandas as pd

        ut1, ut2 = st.tabs(["➕ Create User", "📋 Users List"])

        with ut1:
            st.markdown("#### ➕ Create New User")
            with st.form("admin_create_user", clear_on_submit=True):
                nu1, nu2 = st.columns(2)
                with nu1:
                    nu_user = st.text_input("Username", placeholder="Enter username")
                    nu_email = st.text_input("Email", placeholder="user@company.com")
                with nu2:
                    nu_role = st.selectbox("Role", ["user", "admin"])

                if st.form_submit_button("➕ Create User + Send Temp Password", type="primary"):
                    if nu_user and nu_email:
                        temp_password = None
                        try:
                            temp_password = generate_temp_password()
                            created_user = auth_register(nu_user, temp_password, nu_email, nu_role)
                            set_new_password(created_user["id"], temp_password, True)
                            add_admin_audit_event_fn(
                                actor_user_id=user["id"],
                                actor_username=user["username"],
                                action="user.created",
                                target_type="user",
                                target_id=str(created_user["id"]),
                                target_label=created_user["username"],
                                metadata={"role": nu_role, "email": nu_email.strip().lower()},
                            )

                            if smtp_user and smtp_password:
                                send_email(
                                    smtp_host=smtp_host,
                                    smtp_port=smtp_port,
                                    smtp_user=smtp_user,
                                    smtp_password=smtp_password,
                                    to_email=nu_email.strip(),
                                    subject="PayGlobal AI account created - temporary password",
                                    body=(
                                        f"Hello {nu_user},\n\n"
                                        "Your PayGlobal AI account has been created.\n\n"
                                        f"Username: {nu_user.strip().lower()}\n"
                                        f"Temporary password: {temp_password}\n\n"
                                        "Please log in and change your password immediately.\n"
                                    ),
                                    sendgrid_api_key=sendgrid_api_key,
                                    sendgrid_from_email=sendgrid_from_email,
                                )
                                st.success(f"✅ User **{nu_user}** created as `{nu_role}`. Temporary password emailed.")
                            else:
                                st.warning("User created, but SMTP is not configured. Share temporary password securely.")
                                st.code(f"Username: {nu_user.strip().lower()}\nTemporary password: {temp_password}")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(
                                "User created, but email failed. "
                                "Check SMTP secrets (host/user/password) and try again.\n\n"
                                f"Details: {exc}"
                            )
                            if temp_password:
                                st.warning("Share these temporary credentials securely with the user:")
                                st.code(f"Username: {nu_user.strip().lower()}\nTemporary password: {temp_password}")
                    else:
                        st.error("Username and email are required.")

        with ut2:
            st.markdown("#### 👥 Users")
            all_users = get_all_users_fn()
            df = pd.DataFrame(all_users or [])
            if df.empty:
                st.info("No users found.")
                return

            # Normalize expected columns
            expected = [
                "id",
                "username",
                "email",
                "role",
                "is_active",
                "failed_login_attempts",
                "locked_until",
                "last_login",
                "last_ip",
                "last_location",
                "last_seen_at",
            ]
            for col in expected:
                if col not in df.columns:
                    df[col] = ""

            df["status"] = df["is_active"].apply(lambda v: "Active" if int(v or 0) == 1 else "Disabled")
            view = df[
                [
                    "id",
                    "username",
                    "email",
                    "role",
                    "status",
                    "failed_login_attempts",
                    "locked_until",
                    "last_login",
                    "last_ip",
                    "last_location",
                    "last_seen_at",
                ]
            ].copy()
            view.columns = [
                "ID",
                "Username",
                "Email",
                "Role",
                "Status",
                "Failed",
                "Locked Until",
                "Last Login",
                "IP",
                "Location",
                "Last Seen",
            ]
            view["Locked Until"] = view["Locked Until"].astype(str).str[:19]
            view["Last Login"] = view["Last Login"].astype(str).str[:19]
            view["Last Seen"] = view["Last Seen"].astype(str).str[:19]

            q = st.text_input("Search users", placeholder="Search by username/email…", label_visibility="collapsed")
            if q:
                ql = q.lower().strip()
                view = view[
                    view["Username"].astype(str).str.lower().str.contains(ql)
                    | view["Email"].astype(str).str.lower().str.contains(ql)
                ]

            st.dataframe(view, width="stretch", height=420)

            st.divider()
            st.markdown("#### 🔧 Manage Selected User")
            by_id = {int(u["id"]): u for u in all_users if u and u.get("id") is not None}
            ids = sorted(by_id.keys())
            selected_id = st.selectbox("Select user ID", ids, format_func=lambda x: f"{x} · {by_id[x]['username']}")
            sel_user = by_id[int(selected_id)]
            is_me = sel_user["id"] == user["id"]

            a1, a2, a3, a4 = st.columns([1.2, 1.4, 1.4, 1.0])
            with a1:
                if not is_me:
                    new_role = st.selectbox("Role", ["user", "admin"], index=0 if sel_user["role"] == "user" else 1, key="um_role")
                    if st.button("Apply Role", width="stretch"):
                        if new_role != sel_user["role"]:
                            update_user_role_fn(sel_user["id"], new_role)
                            add_admin_audit_event_fn(
                                actor_user_id=user["id"],
                                actor_username=user["username"],
                                action="user.role_changed",
                                target_type="user",
                                target_id=str(sel_user["id"]),
                                target_label=sel_user["username"],
                                metadata={"new_role": new_role, "old_role": sel_user["role"]},
                            )
                            st.success("Role updated.")
                            st.rerun()
                else:
                    st.caption("You cannot change your own role.")

            with a2:
                if not is_me:
                    pw = st.text_input("Set new password", type="password", key="um_pw", placeholder="New password…")
                    if st.button("Reset Password", width="stretch"):
                        try:
                            validate_password_strength(pw)
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            reset_user_password_fn(sel_user["id"], hash_password(pw))
                            add_admin_audit_event_fn(
                                actor_user_id=user["id"],
                                actor_username=user["username"],
                                action="user.password_reset",
                                target_type="user",
                                target_id=str(sel_user["id"]),
                                target_label=sel_user["username"],
                            )
                            st.success("Password reset.")
                            st.rerun()
                else:
                    st.caption("Use your profile/password change flow.")

            with a3:
                if not is_me:
                    if st.button("Resend Temp Password", width="stretch"):
                        if not sel_user.get("email"):
                            st.error("User has no email.")
                        else:
                            try:
                                temp_password = generate_temp_password()
                                set_new_password(sel_user["id"], temp_password, True)
                                add_admin_audit_event_fn(
                                    actor_user_id=user["id"],
                                    actor_username=user["username"],
                                    action="user.temp_password_resent",
                                    target_type="user",
                                    target_id=str(sel_user["id"]),
                                    target_label=sel_user["username"],
                                    metadata={"email": sel_user.get("email") or ""},
                                )
                                send_email(
                                    smtp_host=smtp_host,
                                    smtp_port=smtp_port,
                                    smtp_user=smtp_user,
                                    smtp_password=smtp_password,
                                    to_email=sel_user["email"],
                                    subject="PayGlobal AI - temporary password reset",
                                    body=(
                                        f"Hello {sel_user['username']},\n\n"
                                        "An administrator has reset your account access.\n\n"
                                        f"Username: {sel_user['username']}\n"
                                        f"Temporary password: {temp_password}\n\n"
                                        "You must change this password immediately after login.\n"
                                    ),
                                    sendgrid_api_key=sendgrid_api_key,
                                    sendgrid_from_email=sendgrid_from_email,
                                )
                                st.success("Temporary password sent.")
                            except Exception as exc:
                                st.error(f"Failed to send: {exc}")
                else:
                    st.caption("You cannot resend your own temp password.")

            with a4:
                if not is_me:
                    active = bool(sel_user.get("is_active", 1))
                    if st.button("Disable" if active else "Enable", width="stretch"):
                        set_user_active_fn(sel_user["id"], not active)
                        add_admin_audit_event_fn(
                            actor_user_id=user["id"],
                            actor_username=user["username"],
                            action="user.disabled" if active else "user.enabled",
                            target_type="user",
                            target_id=str(sel_user["id"]),
                            target_label=sel_user["username"],
                        )
                        st.rerun()
                    if st.button("Unlock", width="stretch"):
                        unlock_user_fn(sel_user["id"])
                        add_admin_audit_event_fn(
                            actor_user_id=user["id"],
                            actor_username=user["username"],
                            action="user.unlocked",
                            target_type="user",
                            target_id=str(sel_user["id"]),
                            target_label=sel_user["username"],
                        )
                        st.rerun()
                    if st.button("Delete", width="stretch"):
                        delete_user_fn(sel_user["id"])
                        add_admin_audit_event_fn(
                            actor_user_id=user["id"],
                            actor_username=user["username"],
                            action="user.deleted",
                            target_type="user",
                            target_id=str(sel_user["id"]),
                            target_label=sel_user["username"],
                        )
                        st.rerun()
                else:
                    st.caption("You cannot disable/delete yourself.")

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

        st.divider()
        st.markdown("#### 📥 Ingest RAW folder (incremental)")
        st.caption("Ingests new/changed files in `data/raw/` using the manifest (no full re-index).")
        if ingest_folder_fn and raw_docs_dir:
            if st.button("Ingest new/changed raw docs", width="stretch", type="primary"):
                with st.spinner("Ingesting raw docs…"):
                    stats = ingest_folder_fn(folder=raw_docs_dir, force=False, batch_size=100, show_progress=False)
                st.session_state.rag_chain = None
                st.success(
                    f"RAW ingest complete: ingested={stats.get('ingested')} skipped={stats.get('skipped')} "
                    f"failed={stats.get('failed')} chunks={stats.get('chunks')}"
                )

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

        st.markdown("#### 🛡️ Admin Actions (Audit)")
        events = get_admin_audit_events_fn(200)
        if not events:
            st.caption("No admin actions recorded yet.")
        else:
            edf = pd.DataFrame(events)
            for col in ["created_at", "actor_username", "action", "target_type", "target_label", "metadata_json"]:
                if col not in edf.columns:
                    edf[col] = ""
            edf = edf[["created_at", "actor_username", "action", "target_type", "target_label", "metadata_json"]]
            edf.columns = ["Timestamp", "Actor", "Action", "Target Type", "Target", "Metadata"]
            edf["Timestamp"] = edf["Timestamp"].astype(str).str[:19]
            edf.index = edf.index + 1
            st.dataframe(edf, width="stretch", height=260)
            csv_bytes = edf.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download Admin Audit CSV",
                data=csv_bytes,
                file_name=f"admin_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch",
            )

        st.divider()
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
