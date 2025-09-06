import streamlit as st
import json, os, time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
LOG_PATH = BASE_DIR / "logs" / "blue_ai_logs.jsonl"
CONV_PATH = BASE_DIR / "conversation-history.json"
RESULTS_PATH = BASE_DIR / "test-result.json"

# --- simple helper to load conversation messages (standardized format) ---
def load_conversation(path: Path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Expect standardized messages (dicts with id, role, ts, content)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def last_n_messages(conv, n=12):
    out = []
    for m in conv[-n:]:
        ts = m.get("ts") if isinstance(m, dict) else None
        try:
            t = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
        except Exception:
            t = str(ts or "")
        out.append({
            "id": (m.get("id") if isinstance(m, dict) else "")[:8],
            "role": m.get("role") if isinstance(m, dict) else "",
            "time": t,
            "content": (m.get("content") if isinstance(m, dict) else str(m))[:220]
        })
    return out

st.set_page_config(page_title="Blue Psychology — Conversation", layout="wide")
st.title("Blue Psychology — Conversation Snapshot")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Recent Messages")
    conv = load_conversation(CONV_PATH)
    if not conv:
        st.info("No conversation-history.json found. Run a test to generate messages.")
    else:
        st.metric("Total messages", len(conv))
        rows = last_n_messages(conv, n=12)
        st.table(rows)

with col2:
    st.subheader("Summary")
    # load summary from last JSONL final_summary or from conversation file (simple heuristic)
    summary = ""
    # try to read last structured event of type 'ai_turn' or 'final_summary' from logs
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
                for raw in reversed(lines[-400:]):
                    try:
                        ev = json.loads(raw)
                        if ev.get("type") in ("final_summary", "ai_turn"):
                            summary = ev.get("conversation_summary") or ev.get("response") or ev.get("response_snippet") or ""
                            if summary:
                                break
                    except Exception:
                        continue
        except Exception:
            summary = ""
    if not summary:
        # fallback: try to get short summary from conversation file
        try:
            if conv and isinstance(conv, list):
                # look for a message with context 'system_intro' or where role == 'assistant' and content length < 400
                for m in reversed(conv):
                    if isinstance(m, dict) and (m.get("role") == "assistant") and len((m.get("content") or "")) < 600:
                        summary = m.get("content")[:800]
                        break
        except Exception:
            summary = ""

    if summary:
        st.write(summary)
    else:
        st.info("No conversation summary found yet.")

st.sidebar.header("Live settings")
st.sidebar.markdown("Auto-refresh by reloading the page. Use the main app to run tests and generate logs.")
    st.subheader("Saved Test Results (test-result.json)")
    results = read_json_file(RESULTS_PATH)
    if results:
        # show top-level keys and counts
        if isinstance(results, dict) and "users" in results:
            st.write(f"Users stored: {len(results.get('users',{}))}")
            # show last saved user entry
            try:
                last_user = list(results.get("users", {}).keys())[-1]
                st.write("Last user ID:", last_user)
                st.json(results["users"][last_user])
            except Exception:
                st.json(results)
        else:
            st.json(results)
    else:
        st.info("No test-result.json found yet.")

st.sidebar.markdown("---")
st.sidebar.markdown("Tips:\n- Open http://localhost:8501 to view UI\n- If you don't see logs, ensure the app is running and `logs/blue_ai_logs.jsonl` exists.")
st.sidebar.markdown("Refresh manually or use auto-refresh.")

# Auto-refresh
st.experimental_rerun() if st.button("Refresh now") else None
time.sleep(refresh)
st.experimental_rerun()
