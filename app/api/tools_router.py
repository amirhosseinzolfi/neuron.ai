from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.chat.tools import (
    create_reminder, refine_reminder, delete_reminder, list_reminders,
    create_task, refine_task, delete_task, list_tasks,
    current_user_id
)

router = APIRouter(prefix="/tools", tags=["Tools"])

# ============================================================================
# REQUEST MODELS
# ============================================================================

class CreateReminderRequest(BaseModel):
    title: str
    datetime_str: str
    priority: str = "normal"
    user_id: str

class UpdateReminderRequest(BaseModel):
    title: Optional[str] = None
    datetime_str: Optional[str] = None
    priority: Optional[str] = None
    user_id: str

class CreateTaskRequest(BaseModel):
    task_title: str
    deadline: Optional[str] = None
    category: str = "general"
    subtasks: Optional[List[str]] = None
    user_id: str

class UpdateTaskRequest(BaseModel):
    task_title: Optional[str] = None
    deadline: Optional[str] = None
    category: Optional[str] = None
    subtasks: Optional[List[str]] = None
    completed: Optional[bool] = None
    user_id: str

# ============================================================================
# REMINDER ENDPOINTS
# ============================================================================

@router.post("/reminders")
async def api_create_reminder(request: CreateReminderRequest):
    token = current_user_id.set(request.user_id)
    try:
        return create_reminder(request.title, request.datetime_str, request.priority)
    finally:
        current_user_id.reset(token)

@router.get("/reminders")
async def api_list_reminders(user_id: str):
    token = current_user_id.set(user_id)
    try:
        return list_reminders()
    finally:
        current_user_id.reset(token)

@router.patch("/reminders/{reminder_id}")
async def api_update_reminder(reminder_id: str, request: UpdateReminderRequest):
    token = current_user_id.set(request.user_id)
    try:
        return refine_reminder(reminder_id, request.title, request.datetime_str, request.priority)
    finally:
        current_user_id.reset(token)

@router.delete("/reminders/{reminder_id}")
async def api_delete_reminder(reminder_id: str, user_id: str):
    token = current_user_id.set(user_id)
    try:
        return delete_reminder(reminder_id)
    finally:
        current_user_id.reset(token)

# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@router.post("/tasks")
async def api_create_task(request: CreateTaskRequest):
    token = current_user_id.set(request.user_id)
    try:
        return create_task(request.task_title, request.deadline, request.category, request.subtasks)
    finally:
        current_user_id.reset(token)

@router.get("/tasks")
async def api_list_tasks(user_id: str):
    token = current_user_id.set(user_id)
    try:
        return list_tasks()
    finally:
        current_user_id.reset(token)

@router.patch("/tasks/{task_id}")
async def api_update_task(task_id: str, request: UpdateTaskRequest):
    token = current_user_id.set(request.user_id)
    try:
        return refine_task(task_id, request.task_title, request.deadline, request.category, request.subtasks, request.completed)
    finally:
        current_user_id.reset(token)

@router.delete("/tasks/{task_id}")
async def api_delete_task(task_id: str, user_id: str):
    token = current_user_id.set(user_id)
    try:
        return delete_task(task_id)
    finally:
        current_user_id.reset(token)
