"""
Brain Service
----------------------------------------------------------------------
Unified cognitive data aggregator and brain state manager for Neuron.
Consolidates:
1. User Profile, demographics, stars, progress (db.py)
2. Psychological test results and analyses (db.py)
3. Vector Long-Term Memory & episodic facts (Mem0 / Qdrant via MemoryService)
4. User Tasks and Reminders (database/tools_data.json)
5. Structured prompt generator for agents and LLMs
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional

import db
from app.services.memory_service import get_memory_service

logger = logging.getLogger("brain_service")

TOOLS_DATA_FILE = "database/tools_data.json"


class BrainService:
    """
    Centralized Brain Service that aggregates all user information and memories
    across databases, vector stores, and tool trackers.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BrainService, cls).__new__(cls)
            return cls._instance

    def _parse_json_safe(self, data: Any) -> Any:
        """Safely parse JSON string, file path, or return original object."""
        if not data:
            return None
        if isinstance(data, (dict, list)):
            return data
        if isinstance(data, str):
            # Check if it is a path to a JSON file
            if data.endswith(".json") and os.path.exists(data):
                try:
                    with open(data, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read json file at {data}: {e}")
            try:
                return json.loads(data)
            except Exception:
                return data
        return data

    def _load_user_tools_data(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Load tasks and reminders saved for the user."""
        if not os.path.exists(TOOLS_DATA_FILE):
            return {"tasks": [], "reminders": []}
        try:
            with open(TOOLS_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_data = data.get(str(user_id), {})
                return {
                    "tasks": user_data.get("tasks", []),
                    "reminders": user_data.get("reminders", [])
                }
        except Exception as e:
            logger.warning(f"Could not load tools data for user {user_id}: {e}")
            return {"tasks": [], "reminders": []}

    def get_user_brain_snapshot(self, user_id: str, query: Optional[str] = None, memory_limit: int = 5) -> Dict[str, Any]:
        """
        Consolidate the user's full cognitive snapshot:
        - Profile & Demographics
        - Psychological Profile
        - Psychological Test Results
        - Purchased Packages
        - Long-Term Vector Memories (semantic search if query provided, else recent)
        - Active Tasks & Reminders
        """
        try:
            chat_id = int(user_id)
        except (ValueError, TypeError):
            chat_id = user_id

        # 1. Base User Profile from db.py
        user_row = None
        if isinstance(chat_id, int):
            try:
                user_row = db.get_user(chat_id)
            except Exception as e:
                logger.error(f"Error fetching user {chat_id} from db: {e}")

        profile_data = user_row or {}
        psychology_profile = self._parse_json_safe(profile_data.get("psychology_profile"))
        parsed_user_profile = self._parse_json_safe(profile_data.get("user_profile"))

        # 2. Test Results from db.py
        test_history = []
        if isinstance(chat_id, int):
            try:
                test_rows = db.get_user_tests(chat_id)
                if test_rows:
                    for r in test_rows:
                        # r has keys: id, test_name, timestamp
                        test_detail = db.get_test_result(r["id"])
                        test_history.append({
                            "id": r["id"],
                            "test_name": r["test_name"],
                            "timestamp": r["timestamp"],
                            "final_analyze": test_detail.get("final_analyze") if test_detail else None,
                            "result_summary": (test_detail.get("result_text") or "")[:300] if test_detail else None
                        })
            except Exception as e:
                logger.warning(f"Error fetching test results for {chat_id}: {e}")

        # 3. Packages from db.py
        packages = []
        if isinstance(chat_id, int):
            try:
                packages = db.get_user_packages(chat_id) or []
            except Exception as e:
                logger.warning(f"Error fetching packages for {chat_id}: {e}")

        # 4. Long-Term Vector Memory from MemoryService (Mem0)
        memories = []
        mem_service = get_memory_service()
        try:
            if query and query.strip():
                memories = mem_service.search_memories(user_id=str(user_id), query=query, limit=memory_limit)
            else:
                memories = mem_service.list_memories(user_id=str(user_id), limit=memory_limit)
        except Exception as e:
            logger.warning(f"Error querying Mem0 memories for {user_id}: {e}")

        # 5. Active Tasks and Reminders
        tools_data = self._load_user_tools_data(str(user_id))

        return {
            "user_id": str(user_id),
            "profile": {
                "chat_id": profile_data.get("chat_id"),
                "username": profile_data.get("username"),
                "first_name": profile_data.get("first_name"),
                "last_name": profile_data.get("last_name"),
                "balance": profile_data.get("balance", 0),
                "progress": profile_data.get("progress", 0),
                "stars": profile_data.get("stars", 0),
                "information": profile_data.get("information"),
                "psychology_profile": psychology_profile,
                "user_profile": parsed_user_profile
            },
            "psychology_tests": test_history,
            "packages": packages,
            "long_term_memories": memories,
            "tasks": tools_data.get("tasks", []),
            "reminders": tools_data.get("reminders", [])
        }

    def build_brain_context_prompt(self, snapshot: Dict[str, Any]) -> str:
        """
        Formats the brain snapshot into a clean Markdown block ready for
        system instruction injection into any LLM or Agent.
        """
        sections = []

        # Profile block
        prof = snapshot.get("profile", {})
        name = f"{prof.get('first_name', '')} {prof.get('last_name', '')}".strip() or prof.get("username") or "کاربر"
        info_lines = [f"- **نام کاربر:** {name}"]
        if prof.get("stars"):
            info_lines.append(f"- **امتیاز (Stars):** {prof.get('stars')}")
        if prof.get("information"):
            info_lines.append(f"- **اطلاعات پایه:** {prof.get('information')}")
        if prof.get("psychology_profile"):
            info_lines.append(f"- **پروفایل روانشناختی:** {json.dumps(prof.get('psychology_profile'), ensure_ascii=False)}")
        sections.append("### مشخصات و پروفایل کاربر:\n" + "\n".join(info_lines))

        # Recent test insights
        tests = snapshot.get("psychology_tests", [])
        if tests:
            test_lines = []
            for t in tests[:3]:
                analysis = t.get("final_analyze") or t.get("result_summary") or "تکمیل شده"
                test_lines.append(f"- **{t.get('test_name')}:** {analysis}")
            sections.append("### سوابق تست‌های روانشناسی کاربر:\n" + "\n".join(test_lines))

        # Long-term vector memories
        memories = snapshot.get("long_term_memories", [])
        if memories:
            mem_lines = []
            for m in memories:
                content = m.get("content") or m.get("memory") or str(m)
                mem_lines.append(f"- {content}")
            sections.append("### حافظه بلندمدت و فکت‌های ذخیره‌شده (Mem0 Brain):\n" + "\n".join(mem_lines))

        # Pending tasks & reminders
        tasks = snapshot.get("tasks", [])
        reminders = snapshot.get("reminders", [])
        if tasks or reminders:
            tool_lines = []
            for task in tasks[:4]:
                tool_lines.append(f"- تسک: {task.get('title') or task.get('task_title')}")
            for rem in reminders[:4]:
                tool_lines.append(f"- یادآور: {rem.get('title')} ({rem.get('datetime_str') or rem.get('datetime')})")
            sections.append("### تسک‌ها و یادآورهای فعال:\n" + "\n".join(tool_lines))

        return "\n\n".join(sections)

    def sync_memory(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
        source: str = "agent",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an interaction in the background into Mem0 long-term memory.
        Does not block API or agent response time.
        """
        if not user_text or not assistant_text:
            return

        combined_meta = {
            "source": source,
            "timestamp": time.time(),
            **(metadata or {})
        }

        def _worker():
            try:
                mem_service = get_memory_service()
                mem_service.store_conversation_turn(
                    user_id=str(user_id),
                    user_text=user_text,
                    assistant_text=assistant_text,
                    metadata=combined_meta
                )
                logger.info(f"Synchronized interaction to Mem0 for user {user_id} via {source}")
            except Exception as e:
                logger.error(f"Failed to sync memory for user {user_id}: {e}", exc_info=True)

        threading.Thread(target=_worker, daemon=True).start()


# Singleton factory accessor
def get_brain_service() -> BrainService:
    return BrainService()

