from flask import Flask, jsonify, send_file, Response, request
import json, pathlib, os

ROOT = pathlib.Path(__file__).parent.resolve()
DEBUG_LOG = ROOT / "debug_log.jsonl"
CONV_HISTORY = ROOT / "conversation-history.json"
RESULTS = ROOT / "test-result.json"

app = Flask("psych-test-debug-ui")

def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                out.append({"raw": line})
    return out

@app.route("/api/logs")
def api_logs():
    return jsonify(read_jsonl(DEBUG_LOG))

@app.route("/api/history")
def api_history():
    if not CONV_HISTORY.exists():
        return jsonify([])
    try:
        return jsonify(json.load(open(CONV_HISTORY, encoding="utf-8")))
    except Exception:
        return jsonify({"error": "could not read conversation-history.json"})

@app.route("/api/results")
def api_results():
    if not RESULTS.exists():
        return jsonify({})
    try:
        return jsonify(json.load(open(RESULTS, encoding="utf-8")))
    except Exception:
        return jsonify({"error": "could not read test-result.json"})

# Simple browser UI
@app.route("/")
def index():
    return """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Psych Test Debug UI</title></head>
<body style="font-family:system-ui,Roboto,Arial;padding:18px;">
<h2>Debug UI — Psych Test</h2>
<p>Endpoints: <a href="/api/logs">/api/logs</a> • <a href="/api/history">/api/history</a> • <a href="/api/results">/api/results</a></p>
<button onclick="fetchLogs()">Reload</button>
<pre id="out" style="white-space:pre-wrap;border:1px solid #ddd;padding:12px;height:60vh;overflow:auto;"></pre>
<script>
async function fetchLogs(){
  const out = document.getElementById('out');
  out.textContent = "Loading logs...";
  try{
    const r = await fetch('/api/logs'); const logs = await r.json();
    out.textContent = JSON.stringify(logs.slice(-200).reverse(), null, 2);
  }catch(e){
    out.textContent = "Error: "+e;
  }
}
fetchLogs();
</script>
</body>
</html>
"""

def start_web_ui():
    # Use port 8080 on localhost — not exposed publicly by default.
    try:
        app.run(host="127.0.0.1", port=8080, debug=False)
    except Exception as e:
        print("Failed to start web UI:", e)

if __name__ == "__main__":
    start_web_ui()
