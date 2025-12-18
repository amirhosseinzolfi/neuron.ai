import time, logging, json, shutil, subprocess, os
from rich.console import Console
from rich.panel import Panel

# Auto test runner for psychology_test module
def _get_option_text(opt):
    if isinstance(opt, dict):
        return opt.get("text") or opt.get("key") or str(opt)
    return str(opt)


def _choose_default_answer(q):
    opts = q.get("options") or []
    if not opts:
        return "(no options)"
    # If numeric scale strings like "1","2",... pick a middle value
    if all(isinstance(o, str) and o.isdigit() for o in opts):
        mid = len(opts) // 2
        return opts[mid]
    # Prefer a clearly labeled default or first option
    for o in opts:
        text = _get_option_text(o)
        if text and text not in ("", None):
            return text
    return _get_option_text(opts[0])


def _maybe_start_streamlit():
    try:
        streamlit_exe = shutil.which("streamlit")
        if not streamlit_exe:
            return False, "streamlit not found"
        ui_path = os.path.join(os.path.dirname(__file__), "streamlit_ui.py")
        cmd = [streamlit_exe, "run", ui_path, "--server.port", "8501", "--server.headless", "true"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(__file__), start_new_session=True)
        return True, "started"
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    console = Console()
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("auto-test-runner")

    try:
        import psychology_test as pt
        import ai_utils
    except Exception as e:
        log.error(f"Failed to import required modules: {e}")
        raise

    tests = pt.all_tests.get("tests", [])
    if not tests:
        log.error("No tests available in test.json")
        raise SystemExit(1)

    console.print(Panel("[bold cyan]Available Tests[/bold cyan]", title="Auto Test Runner"))
    for i, t in enumerate(tests, start=1):
        console.print(f"{i}. {t.get('test_name')} ({t.get('estimated_time','?')})")

    choice = console.input("\nEnter the test number to run automatically (e.g. 1): ")
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(tests):
        console.print("[red]Invalid test number. Exiting.[/red]")
        raise SystemExit(1)

    choice_idx = int(choice) - 1
    selected = tests[choice_idx]
    console.print(Panel(f"Running test: [bold]{selected.get('test_name')}[/bold]", title="Selected Test", border_style="green"))

    # Build synthetic answers for the entire test (no per-question LLM calls)
    answers = []
    for idx, q in enumerate(selected.get("questions", []), start=1):
        chosen = _choose_default_answer(q)
        answers.append({
            "question_id": q.get("id", f"q_{idx}"),
            "question": q.get("question", "(no text)"),
            "selected_option": chosen,
            "original_response": chosen,
            "question_number": idx,
            "timestamp": time.time()
        })

    # Prepare minimal state for summarize_results
    state = pt.tele_initialize("AutoTester", 30, "Synthetic auto-run for testing", test_type=str(choice_idx+1), chat_id=None)
    # Attach minimal conversation history to state for traceability
    state["conversation_history"] = [
        {"role": "system", "content": "auto_test_runner generated summary", "ts": time.time(), "id": "auto-1"},
        {"role": "user", "content": "Synthetic answers provided automatically.", "ts": time.time(), "id": "auto-2"}
    ]

    results_payload = {
        "test_name": selected.get("test_name"),
        "answers": answers,
        "user_name": state.get("user_name"),
        "user_age": state.get("user_age"),
        "user_info": state.get("user_info")
    }

    console.print("[green]Generating final analysis (using app's final summary generator)...[/green]\n")
    # Ensure the state contains the selected test data so the summary generator can use report templates
    try:
        state["test_data"] = selected
    except Exception:
        pass

    # Call the app's final summary generator (may invoke LLM depending on configuration)
    try:
        analysis = ai_utils.summarize_results(state, results_payload)
    except Exception as e:
        log.error(f"Final analysis generator failed: {e}")
        try:
            # fallback to psychology_test's wrapper
            analysis = pt.summarize_results(state, results_payload)
        except Exception:
            analysis = "خطا در تولید خلاصه. لطفاً بعداً امتحان کنید."

    # Save to test-result.json using module helpers
    try:
        all_results = pt.load_test_results()
        user_id_str = "auto_cli"
        entry_key = f"{selected.get('test_name', 'test')}_{int(time.time())}"
        all_results.setdefault("users", {}).setdefault(user_id_str, {})[entry_key] = {
            **results_payload,
            "analysis": analysis,
            "analysis_timestamp": time.time()
        }
        pt.save_test_results(all_results)
        log.info("Saved auto test result to test-result.json")
    except Exception as e:
        log.error(f"Failed to save test results: {e}")

    # Save conversation history for Streamlit UI
    try:
        with open('conversation-history.json', 'w', encoding='utf-8') as fh:
            json.dump(state.get('conversation_history', []), fh, indent=2, ensure_ascii=False)
        log.info("Saved conversation history to conversation-history.json")
    except Exception as e:
        log.error(f"Failed to save conversation history: {e}")

    # Emit a structured log event so Streamlit UI can display it
    try:
        ai_utils._write_structured_event({
            "type": "auto_test_result",
            "test_name": selected.get('test_name'),
            "user": state.get('user_name'),
            "analysis_snippet": analysis[:1000],
            "ts": time.time()
        })
        log.info("Wrote structured auto_test_result event to logs")
    except Exception as e:
        log.error(f"Failed to write structured log: {e}")

    console.print(Panel(analysis, title="Automated Test Final Analysis", border_style="bright_green"))

    # Optionally start Streamlit UI and provide terminal info
    start_ui = console.input("Start Streamlit UI to view logs and results? (y/N): ") or "n"
    if start_ui.strip().lower() == "y":
        ok, msg = _maybe_start_streamlit()
        if ok:
            console.print("[bold green]Streamlit started on http://localhost:8501 — open in browser.[/bold green]")
            console.print("Also tailing the Streamlit UI is not available here; open the URL in your browser.")
        else:
            console.print(f"[red]Could not start Streamlit: {msg}[/red]")

    console.print("[bold blue]Auto run complete.[/bold blue]")