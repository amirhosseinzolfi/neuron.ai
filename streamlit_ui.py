import streamlit as st
import json, os, time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
LOG_PATH = BASE_DIR / "logs" / "blue_ai_logs.jsonl"
CONV_PATH = BASE_DIR / "conversation-history.json"
RESULTS_PATH = BASE_DIR / "test-result.json"

REFRESH = 3  # seconds

st.set_page_config(page_title="Blue Psychology — Live Logs", layout="wide")
st.title("Blue Psychology — Live Debug UI")
st.markdown("Use this page to inspect structured AI turns, conversation history and saved test results.")

def read_last_jsonl(path: Path, limit: int = 200):
    if not path.exists():
        return []
    lines = []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            file_size = fh.tell()
            block_size = 4096
            data = b""
            pos = max(0, file_size - block_size)
            while len(lines) < limit and pos >= 0:
                fh.seek(pos)
                chunk = fh.read(min(block_size, file_size - pos))
                data = chunk + data
                lines = data.splitlines()
                if pos == 0:
                    break
                pos = max(0, pos - block_size)
            # decode last `limit` lines
            out_lines = []
            for raw in lines[-limit:]:
                try:
                    out_lines.append(json.loads(raw.decode("utf-8")))
                except Exception:
                    try:
                        out_lines.append(json.loads(raw))
                    except Exception:
                        out_lines.append({"raw": raw.decode("utf-8", errors="replace")})
            return out_lines
    except Exception as e:
        return [{"error": str(e)}]

def read_json_file(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

# Auto-refresh controls
st.sidebar.header("Live settings")
refresh = st.sidebar.number_input("Auto-refresh (seconds)", min_value=1, max_value=30, value=REFRESH)
max_lines = st.sidebar.number_input("Max log lines", min_value=10, max_value=2000, value=200)

# Layout panels
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Recent Structured Logs")
    logs = read_last_jsonl(LOG_PATH, limit=max_lines)
    if logs:
        # show a compact table of recent events
        for ev in reversed(logs[-200:]):
            ts = ev.get("ts") or ev.get("timestamp") or time.time()
            try:
                ts_h = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_h = str(ts)
            ev_type = ev.get("type", ev.get("logger", "log"))
            with st.expander(f"{ts_h} — {ev_type}", expanded=False):
                st.json(ev)
    else:
        st.info("No logs found yet. Run the app to generate logs.")

with col2:
    st.subheader("Conversation Snapshot")
    conv = read_json_file(CONV_PATH)
    if conv:
        st.write(f"Messages: {len(conv)}")
        st.json(conv[-40:])  # last 40 messages
    else:
        st.info("No conversation-history.json found yet.")

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
