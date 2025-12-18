import json
import os
from datetime import datetime
from typing import Any, List, Optional, Dict
from uuid import uuid4
import contextvars

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ============================================================================
# CONTEXT & PERSISTENCE
# ============================================================================

# Context variable to hold the current user_id during tool execution
current_user_id = contextvars.ContextVar("user_id", default="default")

TOOLS_DATA_FILE = "database/tools_data.json"

def _load_data() -> Dict[str, Any]:
    if not os.path.exists(TOOLS_DATA_FILE):
        return {}
    try:
        with open(TOOLS_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_data(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(TOOLS_DATA_FILE), exist_ok=True)
    with open(TOOLS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _get_user_storage(key: str) -> List[Dict]:
    data = _load_data()
    user_id = current_user_id.get()
    user_data = data.get(user_id, {})
    return user_data.get(key, [])

def _save_user_storage(key: str, items: List[Dict]):
    data = _load_data()
    user_id = current_user_id.get()
    if user_id not in data:
        data[user_id] = {}
    data[user_id][key] = items
    _save_data(data)

# ============================================================================
# SCHEMAS
# ============================================================================

class ReminderExtraction(BaseModel):
    """Extracted reminder information."""
    title: str = Field(description="What is the reminder about?")
    datetime: str = Field(description="When should it trigger? (ISO format)")
    priority: str = Field(default="normal", description="Priority: low, normal, high")

class TaskExtraction(BaseModel):
    """Extracted task/todo."""
    task_title: str = Field(description="What is the task?")
    deadline: Optional[str] = Field(default=None, description="Deadline (ISO format)")
    category: str = Field(default="general", description="Category: work, personal, shopping")
    subtasks: List[str] = Field(default_factory=list, description="Any subtasks?")

# ============================================================================
# REMINDER TOOLS
# ============================================================================

@tool
def create_reminder(
    title: str,
    datetime_str: str,
    priority: str = "normal"
) -> dict:
    """Create and save a new reminder.
    
    Args:
        title: What is the reminder about?
        datetime_str: When to trigger? (ISO format, e.g., 2024-12-25T14:30:00)
        priority: Priority level: low, normal, high
    """
    reminder_id = str(uuid4())
    extraction = {
        "id": reminder_id,
        "type": "reminder",
        "title": title,
        "datetime": datetime_str,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    reminders = _get_user_storage("reminders")
    reminders.append(extraction)
    _save_user_storage("reminders", reminders)
    
    return {
        "status": "saved",
        "action": "create",
        "reminder_id": reminder_id,
        "extraction": extraction
    }

@tool
def refine_reminder(
    reminder_id: str,
    title: Optional[str] = None,
    datetime_str: Optional[str] = None,
    priority: Optional[str] = None
) -> dict:
    """Update/refine an existing reminder.
    
    Args:
        reminder_id: ID of the reminder to update
        title: New title (optional)
        datetime_str: New datetime (optional, ISO format)
        priority: New priority level (optional)
    """
    reminders = _get_user_storage("reminders")
    
    reminder_found = False
    for reminder in reminders:
        if reminder["id"] == reminder_id:
            reminder_found = True
            if title is not None:
                reminder["title"] = title
            if datetime_str is not None:
                reminder["datetime"] = datetime_str
            if priority is not None:
                reminder["priority"] = priority
            reminder["updated_at"] = datetime.now().isoformat()
            break
    
    if not reminder_found:
        return {
            "status": "error",
            "action": "refine",
            "message": f"Reminder with ID {reminder_id} not found"
        }
    
    _save_user_storage("reminders", reminders)
    
    return {
        "status": "updated",
        "action": "refine",
        "reminder_id": reminder_id,
        "message": "Reminder updated successfully"
    }

@tool
def delete_reminder(reminder_id: str) -> dict:
    """Delete a reminder by ID.
    
    Args:
        reminder_id: ID of the reminder to delete
    """
    reminders = _get_user_storage("reminders")
    initial_count = len(reminders)
    reminders = [r for r in reminders if r["id"] != reminder_id]
    
    if len(reminders) == initial_count:
        return {
            "status": "error",
            "action": "delete",
            "message": f"Reminder with ID {reminder_id} not found"
        }
    
    _save_user_storage("reminders", reminders)
    
    return {
        "status": "deleted",
        "action": "delete",
        "reminder_id": reminder_id,
        "message": "Reminder deleted successfully"
    }

@tool
def list_reminders() -> dict:
    """List all reminders for the current user."""
    reminders = _get_user_storage("reminders")
    return {
        "status": "success",
        "count": len(reminders),
        "reminders": reminders
    }

# ============================================================================
# TASK TOOLS
# ============================================================================

@tool
def create_task(
    task_title: str,
    deadline: Optional[str] = None,
    category: str = "general",
    subtasks: Optional[List[str]] = None
) -> dict:
    """Create and save a new task/todo.
    
    Args:
        task_title: What is the task?
        deadline: When is it due? (ISO format, optional)
        category: Category: work, personal, shopping, etc.
        subtasks: List of subtasks (optional)
    """
    task_id = str(uuid4())
    extraction = {
        "id": task_id,
        "type": "task",
        "task_title": task_title,
        "deadline": deadline,
        "category": category,
        "subtasks": subtasks or [],
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "completed": False
    }
    
    tasks = _get_user_storage("tasks")
    tasks.append(extraction)
    _save_user_storage("tasks", tasks)
    
    return {
        "status": "saved",
        "action": "create",
        "task_id": task_id,
        "extraction": extraction
    }

@tool
def refine_task(
    task_id: str,
    task_title: Optional[str] = None,
    deadline: Optional[str] = None,
    category: Optional[str] = None,
    subtasks: Optional[List[str]] = None,
    completed: Optional[bool] = None
) -> dict:
    """Update/refine an existing task.
    
    Args:
        task_id: ID of the task to update
        task_title: New title (optional)
        deadline: New deadline (optional, ISO format)
        category: New category (optional)
        subtasks: New subtasks list (optional)
        completed: Mark as completed (optional)
    """
    tasks = _get_user_storage("tasks")
    
    task_found = False
    for task in tasks:
        if task["id"] == task_id:
            task_found = True
            if task_title is not None:
                task["task_title"] = task_title
            if deadline is not None:
                task["deadline"] = deadline
            if category is not None:
                task["category"] = category
            if subtasks is not None:
                task["subtasks"] = subtasks
            if completed is not None:
                task["completed"] = completed
                task["status"] = "completed" if completed else "active"
            task["updated_at"] = datetime.now().isoformat()
            break
    
    if not task_found:
        return {
            "status": "error",
            "action": "refine",
            "message": f"Task with ID {task_id} not found"
        }
    
    _save_user_storage("tasks", tasks)
    
    return {
        "status": "updated",
        "action": "refine",
        "task_id": task_id,
        "message": "Task updated successfully"
    }

@tool
def delete_task(task_id: str) -> dict:
    """Delete a task by ID.
    
    Args:
        task_id: ID of the task to delete
    """
    tasks = _get_user_storage("tasks")
    initial_count = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    
    if len(tasks) == initial_count:
        return {
            "status": "error",
            "action": "delete",
            "message": f"Task with ID {task_id} not found"
        }
    
    _save_user_storage("tasks", tasks)
    
    return {
        "status": "deleted",
        "action": "delete",
        "task_id": task_id,
        "message": "Task deleted successfully"
    }

@tool
def list_tasks() -> dict:
    """List all tasks for the current user."""
    tasks = _get_user_storage("tasks")
    return {
        "status": "success",
        "count": len(tasks),
        "tasks": tasks
    }

ALL_TOOLS = [
    create_reminder, refine_reminder, delete_reminder, list_reminders,
    create_task, refine_task, delete_task, list_tasks
]
