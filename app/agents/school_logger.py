"""
School Assistant Rich Logging Engine
----------------------------------------------------------------------
Provides structured, readable, and colorful terminal logging for
the School Assistant agent, daily missions, homework evaluations,
and 12-day coaching progress tracking.
Safe against Windows console cp1252 encoding limitations.
"""

from typing import Dict, Any, List, Optional
import sys
import logging

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger("school_assistant")

try:
    console = Console(highlight=False, soft_wrap=True)
except Exception:
    console = None


def _safe_print(renderable):
    """Safely print to console without crashing on Windows charmap errors."""
    if not console:
        return
    try:
        console.print(renderable)
    except Exception as e:
        logger.debug(f"Console print fallback: {e}")


def log_student_session_start(user_id: str, message: str, current_day: int = 1, status: str = "active"):
    """Logs the beginning of an interaction turn with the student."""
    try:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bright_white")

        day_badge = f"[bold white on bright_blue] روز {current_day} از ۱۲ [/bold white on bright_blue]"
        status_color = "green" if status == "active" else ("gold1" if status == "completed" else "yellow")
        status_badge = f"[{status_color}]● {status.upper()}[/{status_color}]"

        clean_msg = message.strip() if message else "(بدون متن)"
        if len(clean_msg) > 120:
            clean_msg = clean_msg[:117] + "..."

        table.add_row("شناسه دانش‌آموز:", f"[bold yellow]{user_id}[/bold yellow]  {day_badge}  {status_badge}")
        table.add_row("پیام دریافتی:", f"[italic]{clean_msg}[/italic]")

        _safe_print("")
        _safe_print(Panel(
            table,
            title="[bold bright_cyan]نیورون | مربی تحصیلی ۱۲ روزه (School Assistant)[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(0, 2)
        ))
    except Exception as e:
        logger.info(f"[SchoolAssistant] User {user_id} | Day {current_day} | Message: {message[:60]}")


def log_tool_execution(tool_name: str, args: Dict[str, Any]):
    """Logs a tool call with its arguments."""
    try:
        arg_lines = []
        for k, v in args.items():
            if v is not None and str(v).strip():
                val_str = str(v)
                if len(val_str) > 80:
                    val_str = val_str[:77] + "..."
                arg_lines.append(f"[dim]{k}:[/dim] [bright_white]{val_str}[/bright_white]")

        args_rendered = " | ".join(arg_lines) if arg_lines else "[dim]بدون پارامتر ورودی[/dim]"
        _safe_print(
            f"  [bold yellow]>> فراخوانی ابزار:[/bold yellow] [bold bright_magenta]{tool_name}[/bold bright_magenta] "
            f"({args_rendered})"
        )
    except Exception:
        logger.info(f"[SchoolAssistant Tool] {tool_name} args={args}")


def log_plan_generated(plan: Dict[str, Any]):
    """Prints a beautiful summary table of a newly generated 12-day curriculum."""
    try:
        goal = plan.get("curriculum_goal", "رشد تحصیلی و انضباط مطالعه")
        student = plan.get("student_name", "دانش‌آموز")
        days = plan.get("days", [])

        table = Table(
            title=f"سرفصل دوره ۱۲ روزه تحصیلی برای {student}",
            title_style="bold green",
            header_style="bold bright_blue",
            border_style="cyan",
            show_lines=True
        )
        table.add_column("روز", justify="center", style="bold yellow", width=8)
        table.add_column("موضوع و سرفصل تمرین", style="bright_white", width=34)
        table.add_column("تکلیف شبانه", style="dim", width=42)

        for d in days:
            day_num = d.get("day", "?")
            theme = d.get("theme", "")
            hw = d.get("homework_assignment", "")
            if len(hw) > 60:
                hw = hw[:57] + "..."
            table.add_row(f"روز {day_num}", theme, hw)

        _safe_print(Panel(
            table,
            title=f"[bold green]برنامه ۱۲ روزه اختصاصی با موفقیت ساخته شد[/bold green] | [italic]{goal}[/italic]",
            border_style="green",
            padding=(1, 1)
        ))
    except Exception as e:
        logger.info(f"[SchoolAssistant Plan Generated] {plan.get('curriculum_goal')}")


def log_homework_evaluation(day: int, score: int, passed: bool, feedback: str, strengths: List[str] = None, improvements: List[str] = None):
    """Prints a structured card showing homework grading and progression decision."""
    try:
        badge = "[bold white on green] قبولی در مرحله [OK] [/bold white on green]" if passed else "[bold white on red] نیاز به بازنگری [/bold white on red]"
        score_color = "bright_green" if score >= 75 else ("yellow" if score >= 60 else "bright_red")

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold cyan", justify="right")
        table.add_column(style="bright_white")

        table.add_row("وضعیت تکلیف:", f"روز {day} از ۱۲ | {badge} | نمره: [{score_color}]{score}/100[/{score_color}]")
        table.add_row("بازخورد مربی:", f"[italic]{feedback}[/italic]")

        if strengths:
            table.add_row("نقاط قوت:", f"[green]{' • '.join(strengths)}[/green]")
        if improvements:
            table.add_row("نیاز به اصلاح:", f"[yellow]{' • '.join(improvements)}[/yellow]")

        _safe_print(Panel(
            table,
            title=f"[bold]ارزیابی تکلیف روز {day}[/bold]",
            border_style="green" if passed else "red",
            padding=(0, 2)
        ))
    except Exception as e:
        logger.info(f"[SchoolAssistant Homework] Day {day} Score={score} Passed={passed}")


def log_day_progression(old_day: int, new_day: int, total_days: int = 12):
    """Celebration log when a student unlocks the next coaching day."""
    try:
        if new_day > total_days:
            _safe_print(Panel(
                f"[bold bright_green]تبریک صمیمانه! دوره ۱۲ روزه با موفقیت کامل به پایان رسید![/bold bright_green]\n"
                f"[bright_white]شما تمامی ۱۲ گام رشد تحصیلی را پشت سر گذاشتید و عادات مطالعه پایدار ساختید.[/bright_white]",
                border_style="gold1",
                padding=(1, 2)
            ))
        else:
            _safe_print(
                f"  [bold bright_green]>> صعود به مرحله بعد:[/bold bright_green] "
                f"[dim]روز {old_day}[/dim] -> [bold bright_magenta]روز {new_day} از {total_days} باز شد![/bold bright_magenta]"
            )
    except Exception:
        logger.info(f"[SchoolAssistant Progression] Day {old_day} -> Day {new_day}")


def log_graduation_report(report: Dict[str, Any]):
    """Logs the final 12-day graduation performance report."""
    try:
        student = report.get("student_name", "دانش‌آموز")
        score = report.get("overall_score", 90)
        summary = report.get("executive_summary", "")
        strengths = report.get("strengths_mastered", [])
        habits = report.get("habits_built", [])
        roadmap = report.get("future_action_plan", [])
        coach_msg = report.get("final_coach_message", "")

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold gold1", justify="right")
        table.add_column(style="bright_white")

        table.add_row("دانش‌آموز:", f"[bold]{student}[/bold] | امتیاز کل: [bold bright_green]{score}/100[/bold bright_green]")
        table.add_row("خلاصه تحول:", f"{summary}")
        if strengths:
            table.add_row("مهارت‌های تثبیت‌شده:", f"[bright_cyan]{' • '.join(strengths)}[/bright_cyan]")
        if habits:
            table.add_row("عادات ساخته‌شده:", f"[green]{' • '.join(habits)}[/green]")
        if roadmap:
            table.add_row("نقشه راه آینده:", f"[yellow]{' • '.join(roadmap)}[/yellow]")
        if coach_msg:
            table.add_row("پیام پایانی مربی:", f"[italic bright_yellow]«{coach_msg}»[/italic bright_yellow]")

        _safe_print(Panel(
            table,
            title="[bold gold1]کارنامه جامع پایان دوره ۱۲ روزه تحصیلی[/bold gold1]",
            border_style="gold1",
            padding=(1, 2)
        ))
    except Exception as e:
        logger.info(f"[SchoolAssistant Report] Student={report.get('student_name')} Score={report.get('overall_score')}")


def log_brain_and_memory_context(brain_snapshot: Dict[str, Any], instruction_preview: str = ""):
    """Logs the injected memory, user profile, and system instruction."""
    try:
        prof = (brain_snapshot or {}).get("profile", {})
        tests = (brain_snapshot or {}).get("psychology_tests", [])
        mems = (brain_snapshot or {}).get("long_term_memories", [])
        tasks = (brain_snapshot or {}).get("tasks", [])
        reminders = (brain_snapshot or {}).get("reminders", [])

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold cyan", justify="right", width=22)
        table.add_column(style="bright_white")

        # 1. Profile
        name = f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip() or prof.get("username") or "کاربر"
        info = prof.get("information") or "ثبت‌نشده"
        stars = prof.get("stars", 0)
        table.add_row("👤 هویت و پروفایل کاربر:", f"[bold]{name}[/bold] (اطلاعات: {info} | امتیاز/ستاره: {stars})")

        # 2. Psych profile
        psych = prof.get("psychology_profile")
        if psych:
            psych_desc = str(psych)[:100] + ("..." if len(str(psych)) > 100 else "")
            table.add_row("🧠 پروفایل روانشناختی:", f"[dim]{psych_desc}[/dim]")

        # 3. Psych tests
        if tests:
            test_names = [t.get("test_name", "تست") for t in tests[:3]]
            table.add_row("🧪 سوابق تست‌های روانی:", f"[bright_yellow]{', '.join(test_names)}[/bright_yellow] ({len(tests)} تست در دیتابیس)")
        else:
            table.add_row("🧪 سوابق تست‌های روانی:", "[dim]بدون سابقه تست قبلی[/dim]")

        # 4. Long-term vector memories (Mem0)
        if mems:
            mem_bullets = [f"• {m.get('content') or m.get('memory') or str(m)}" for m in mems[:3]]
            table.add_row("💾 حافظه برداری Mem0:", f"[bright_cyan]{' | '.join(mem_bullets)}[/bright_cyan] ({len(mems)} فکت مرتبط)")
        else:
            table.add_row("💾 حافظه برداری Mem0:", "[dim]فکت ذخیره‌شده جدیدی یافت نشد[/dim]")

        # 5. Tasks/Reminders
        table.add_row("📌 تسک‌ها و یادآورها:", f"[dim]{len(tasks)} تسک فعال | {len(reminders)} یادآور[/dim]")

        # 6. System Instruction
        if instruction_preview:
            clean_inst = instruction_preview.replace("\n", " ").strip()
            if len(clean_inst) > 130:
                clean_inst = clean_inst[:127] + "..."
            table.add_row("📜 دستورالعمل سیستم:", f"[italic dim]{clean_inst}[/italic dim]")

        _safe_print(Panel(
            table,
            title="🧠 [bold bright_cyan]کانتکست مغز و حافظه کاربر (User Brain & Memory Context)[/bold bright_cyan]",
            border_style="cyan",
            padding=(0, 2)
        ))
    except Exception as e:
        logger.debug(f"Brain context log fallback: {e}")


def log_turn_telemetry(ai_calls_count: int, input_tokens: int, output_tokens: int, duration_sec: float = 0.0):
    """Prints a structured summary of AI requests count, token usage, and latency."""
    try:
        total_tokens = input_tokens + output_tokens

        table = Table(
            title="📊 آمار مصرف توکن و درخواست‌های هوش مصنوعی (Turn Telemetry)",
            title_style="bold bright_blue",
            header_style="bold cyan",
            border_style="bright_blue",
            show_lines=False
        )
        table.add_column("تعداد درخواست AI", justify="center", style="bold yellow")
        table.add_column("توکن ورودی (Input)", justify="center", style="bright_white")
        table.add_column("توکن خروجی (Output)", justify="center", style="bright_white")
        table.add_column("مجموع توکن‌ها", justify="center", style="bold bright_green")
        table.add_column("مدت زمان پردازش", justify="center", style="dim")

        table.add_row(
            f"{ai_calls_count} درخواست",
            f"{input_tokens:,}",
            f"{output_tokens:,}",
            f"{total_tokens:,}",
            f"{duration_sec:.2f} ثانیه" if duration_sec > 0 else "-"
        )

        _safe_print(table)
    except Exception as e:
        logger.info(f"[Turn Telemetry] AI Calls={ai_calls_count} Tokens={input_tokens}+{output_tokens}")


