import db2 as db


def test_feedback_upsert_single_vote_per_user(isolated_db):
    user_id = db.create_user("tester", "hashed_pw", "tester@example.com", "user")
    conv_id = db.create_conversation(user_id, "Test Chat", "All Modules")
    msg_id = db.save_message(conv_id, "assistant", "Answer", [])

    db.save_feedback(msg_id, user_id, 1)
    db.save_feedback(msg_id, user_id, -1)

    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, MAX(rating) AS rating FROM feedback WHERE message_id = ? AND user_id = ?",
            (msg_id, user_id),
        ).fetchone()

    # sqlite driver may return row tuple in SQLAlchemy raw_connection mode
    cnt = row["cnt"] if not isinstance(row, tuple) else row[0]
    rating = row["rating"] if not isinstance(row, tuple) else row[1]
    assert cnt == 1
    assert rating == -1
