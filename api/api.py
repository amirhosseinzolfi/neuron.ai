"""
FastAPI Server for Blue Psychology Test Bot
============================================

This API provides REST endpoints for all core functionalities of the psychology test system.

Architecture Overview:
- Psychology Tests: Interactive test-taking and result retrieval
- Smart Chat: AI-powered conversational therapy sessions
- User Management: Profile, wallet, and test history
- Image Generation: AI-generated personality visualizations
- Package System: Test bundles and purchases

Endpoints are organized by feature domain and follow RESTful conventions.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Body
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import os
import sys
import time
import json
import io
from datetime import datetime

# Add parent directory to path to import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
import db
import psychology_test as pt
from app.chat.smart_chat import get_memory, get_chat_agent, chat
from ai_utils import (
    generate_image_prompt, 
    summarize_results, 
    update_user_profile_with_ai,
    analyze_final_result
)
from image_utils import generate_images_for_prompt
from pdf_utils import generate_pdf

# Initialize FastAPI app
app = FastAPI(
    title="Blue Psychology Test API",
    description="REST API for psychology tests, AI chat therapy, and user management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db.init_db()

# Initialize smart chat components (lazy loaded)
_memory = None
_agent = None

def get_smart_chat_agent():
    """Lazy initialization of smart chat agent"""
    global _memory, _agent
    if _memory is None:
        _memory = get_memory()
    if _agent is None:
        _agent = get_chat_agent(_memory)
    return _agent

# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class UserCreate(BaseModel):
    """User registration/creation"""
    chat_id: int = Field(..., description="Telegram chat ID or unique user identifier")
    username: Optional[str] = Field(None, description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")

class UserProfile(BaseModel):
    """User profile update"""
    progress: Optional[int] = Field(None, description="Progress indicator")
    information: Optional[str] = Field(None, description="Additional user information")
    stars: Optional[int] = Field(None, description="User rating/stars")

class BalanceUpdate(BaseModel):
    """Wallet balance modification"""
    chat_id: int
    amount: int = Field(..., description="Amount to add (positive) or subtract (negative)")

class TestInitialize(BaseModel):
    """Initialize a new test session"""
    user_name: str = Field(..., description="User's name")
    age: int = Field(..., ge=1, le=150, description="User's age")
    user_info: str = Field("", description="Additional context about the user")
    test_type: str = Field("1", description="Test ID or type (1, 2, 3, etc.)")
    chat_id: Optional[int] = Field(None, description="Optional chat ID for session tracking")

class TestAnswer(BaseModel):
    """Submit an answer to a test question"""
    session_id: str = Field(..., description="Test session identifier")
    user_input: str = Field(..., description="User's answer text")

class ChatMessage(BaseModel):
    """Smart chat message"""
    user_id: str = Field(..., description="Unique user identifier for conversation thread")
    message: str = Field(..., description="User message text")

class ImageGenerationRequest(BaseModel):
    """Generate personality image"""
    prompt: str = Field(..., description="Text prompt for image generation")
    user_name: str = Field(..., description="User name for file naming")
    model: str = Field("flux", description="Image model: flux, midjourney, dall-e-3, etc.")
    num_images: int = Field(1, ge=1, le=5, description="Number of images to generate")
    width: int = Field(512, ge=256, le=1024, description="Image width")
    height: int = Field(512, ge=256, le=1024, description="Image height")

class PackagePurchase(BaseModel):
    """Purchase a test package"""
    chat_id: int
    package_id: str = Field(..., description="Package identifier")
    test_ids: List[int] = Field(..., description="List of test IDs in the package")

# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/", tags=["General"])
async def root():
    """API root endpoint with basic info"""
    return {
        "message": "Blue Psychology Test API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "tests": "/tests",
            "chat": "/chat",
            "users": "/users",
            "images": "/images",
            "packages": "/packages"
        }
    }

@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        users = db.get_all_users()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": "operational",
                "api": "operational"
            },
            "stats": {
                "total_users": len(users)
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ============================================================================
# TEST MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/tests", tags=["Tests"], response_model=Dict[str, Any])
async def list_tests():
    """
    List all available psychology tests
    
    Returns test catalog with metadata like name, duration, and question count.
    """
    try:
        all_tests = pt.get_all_tests()
        return {
            "success": True,
            "tests": all_tests.get("tests", []),
            "count": len(all_tests.get("tests", []))
        }
    except Exception as e:
        logger.error(f"Error listing tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tests/{test_id}", tags=["Tests"])
async def get_test_details(test_id: int):
    """
    Get detailed information about a specific test
    
    Returns test structure including questions and options (without showing answers).
    """
    try:
        tests = pt.get_test_list()
        if test_id < 1 or test_id > len(tests):
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
        
        test = tests[test_id - 1]
        return {
            "success": True,
            "test": test
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tests/initialize", tags=["Tests"])
async def initialize_test(request: TestInitialize):
    """
    Initialize a new test session
    
    Creates a test state and returns the first question.
    Session ID is generated for tracking progress.
    """
    try:
        # Create test state
        state = pt.tele_initialize(
            user_name=request.user_name,
            age=request.age,
            user_info=request.user_info,
            test_type=request.test_type,
            chat_id=request.chat_id
        )
        
        # Generate session ID
        session_id = f"{request.chat_id or 'anon'}_{int(time.time())}"
        
        # Store state in memory (in production, use Redis or database)
        # For now, we'll use a simple in-memory dict
        if not hasattr(app, 'test_sessions'):
            app.test_sessions = {}
        app.test_sessions[session_id] = state
        
        # Get first question
        first_question = pt.tele_get_question(state)
        
        return {
            "success": True,
            "session_id": session_id,
            "test_name": state["test_data"]["test_name"],
            "total_questions": len(state["test_data"]["questions"]),
            "current_question": state["current_question"] + 1,
            "question_text": first_question
        }
    except Exception as e:
        logger.error(f"Error initializing test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tests/answer", tags=["Tests"])
async def submit_answer(request: TestAnswer):
    """
    Submit an answer to a test question
    
    Validates the answer and returns either:
    - The next question if valid
    - A retry message if invalid
    - Test completion status if this was the last question
    """
    try:
        # Retrieve session state
        if not hasattr(app, 'test_sessions') or request.session_id not in app.test_sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please initialize a new test.")
        
        state = app.test_sessions[request.session_id]
        
        # Process answer
        result = pt.tele_process_answer(state, request.user_input)
        
        # Update stored state
        app.test_sessions[request.session_id] = state
        
        # Check if test is finished
        if state.get("finished"):
            # Generate summary
            summary = pt.tele_summarize(state)
            
            # Generate analysis caption
            try:
                analysis_caption = analyze_final_result(state, summary)
            except Exception as e:
                logger.error(f"Failed to generate analysis caption: {e}")
                analysis_caption = summary[:500]  # Fallback to truncated summary
            
            # Clean up session
            del app.test_sessions[request.session_id]
            
            return {
                "success": True,
                "finished": True,
                "summary": summary,
                "analysis": analysis_caption,
                "test_results": state.get("test_results", {})
            }
        
        # Return next question or retry message
        if result.get("ack"):
            return {
                "success": False,
                "finished": False,
                "retry_message": result["ack"],
                "current_question": state["current_question"] + 1
            }
        else:
            return {
                "success": True,
                "finished": False,
                "current_question": state["current_question"] + 1,
                "total_questions": len(state["test_data"]["questions"]),
                "question_text": result.get("next")
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/users", tags=["Users"], status_code=201)
async def create_user(user: UserCreate):
    """
    Create or update a user
    
    Registers a new user or updates existing user metadata.
    """
    try:
        db.save_user(
            chat_id=user.chat_id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or ""
        )
        
        return {
            "success": True,
            "message": "User created/updated successfully",
            "chat_id": user.chat_id
        }
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{chat_id}", tags=["Users"])
async def get_user(chat_id: int):
    """
    Get user profile and statistics
    
    Returns complete user profile including balance, tests taken, and metadata.
    """
    try:
        user_data = db.get_user(chat_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's test history
        tests = db.get_user_tests(chat_id)
        
        return {
            "success": True,
            "user": user_data,
            "test_count": len(tests),
            "tests": [dict(t) for t in tests]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/users/{chat_id}/profile", tags=["Users"])
async def update_user_profile(chat_id: int, profile: UserProfile):
    """
    Update user profile information
    
    Updates progress, information, or star rating.
    """
    try:
        updates = profile.dict(exclude_none=True)
        success = db.update_user_profile(chat_id, **updates)
        
        if not success:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "updated_fields": list(updates.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{chat_id}/balance", tags=["Users", "Wallet"])
async def get_balance(chat_id: int):
    """Get user's wallet balance"""
    try:
        balance = db.get_balance(chat_id)
        return {
            "success": True,
            "chat_id": chat_id,
            "balance": balance
        }
    except Exception as e:
        logger.error(f"Error getting balance for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/balance", tags=["Users", "Wallet"])
async def update_balance(request: BalanceUpdate):
    """
    Update user's wallet balance
    
    Add or subtract credits from user's wallet.
    """
    try:
        db.update_balance(request.chat_id, request.amount)
        new_balance = db.get_balance(request.chat_id)
        
        return {
            "success": True,
            "message": f"Balance updated by {request.amount}",
            "new_balance": new_balance
        }
    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{chat_id}/tests", tags=["Users", "Tests"])
async def get_user_test_history(chat_id: int):
    """
    Get user's test history
    
    Returns list of all tests taken by the user with timestamps.
    """
    try:
        tests = db.get_user_tests(chat_id)
        return {
            "success": True,
            "chat_id": chat_id,
            "test_count": len(tests),
            "tests": [dict(t) for t in tests]
        }
    except Exception as e:
        logger.error(f"Error getting test history for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{chat_id}/tests/{result_id}", tags=["Users", "Tests"])
async def get_test_result(chat_id: int, result_id: int):
    """
    Get specific test result details
    
    Returns full test result including summary and analysis.
    """
    try:
        result = db.get_test_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Test result not found")
        
        return {
            "success": True,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test result {result_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{chat_id}/tests/{result_id}/pdf", tags=["Users", "Tests"])
async def download_test_pdf(chat_id: int, result_id: int):
    """
    Download test result as PDF
    
    Returns PDF file of the test result if available.
    """
    try:
        result = db.get_test_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Test result not found")
        
        pdf_path = result.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"test_result_{result_id}.pdf"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading PDF for result {result_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SMART CHAT ENDPOINTS
# ============================================================================

@app.post("/chat", tags=["Smart Chat"])
async def send_chat_message(message: ChatMessage):
    """
    Send message to smart AI chat therapist
    
    Maintains conversation context and provides personalized responses.
    Each user_id has its own conversation thread.
    """
    try:
        agent = get_smart_chat_agent()
        
        # Send message and get response
        response = chat(agent, message.user_id, message.message)
        
        # Handle different response types
        if isinstance(response, dict):
            # Response has both raw and refined versions
            return {
                "success": True,
                "user_id": message.user_id,
                "response": response.get("refined", response.get("raw", "")),
                "raw_response": response.get("raw", "")
            }
        elif isinstance(response, str):
            # Simple string response
            return {
                "success": True,
                "user_id": message.user_id,
                "response": response
            }
        elif isinstance(response, list):
            # Conversation history returned (empty message case)
            return {
                "success": True,
                "user_id": message.user_id,
                "history": [
                    {
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": msg.content if hasattr(msg, "content") else str(msg)
                    }
                    for msg in response
                ]
            }
        else:
            return {
                "success": True,
                "user_id": message.user_id,
                "response": str(response)
            }
    except Exception as e:
        logger.error(f"Error in chat for user {message.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/{user_id}/history", tags=["Smart Chat"])
async def get_chat_history(user_id: str):
    """
    Get conversation history for a user
    
    Returns full conversation thread with the AI therapist.
    """
    try:
        agent = get_smart_chat_agent()
        
        # Get history by sending empty message
        history = chat(agent, user_id, "")
        
        if isinstance(history, list):
            return {
                "success": True,
                "user_id": user_id,
                "message_count": len(history),
                "history": [
                    {
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": msg.content if hasattr(msg, "content") else str(msg)
                    }
                    for msg in history
                ]
            }
        else:
            return {
                "success": True,
                "user_id": user_id,
                "message_count": 0,
                "history": []
            }
    except Exception as e:
        logger.error(f"Error getting chat history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/{user_id}/history", tags=["Smart Chat"])
async def clear_chat_history(user_id: str):
    """
    Clear conversation history for a user
    
    Resets the conversation thread (useful for starting fresh sessions).
    """
    try:
        # This would require implementing a clear method in smart_chat.py
        # For now, we'll return a message indicating manual database cleanup is needed
        return {
            "success": True,
            "message": "To clear history, restart the conversation with a new user_id or implement database cleanup",
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Error clearing chat history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# IMAGE GENERATION ENDPOINTS
# ============================================================================

@app.post("/images/generate", tags=["Images"])
async def generate_personality_image(request: ImageGenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate AI personality visualization images
    
    Creates images based on personality analysis using various AI models.
    Supports: flux, midjourney, dall-e-3, sdxl, and more.
    """
    try:
        output_dir = "generated_images"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate images
        image_paths = generate_images_for_prompt(
            prompt=request.prompt,
            user_name=request.user_name,
            out_dir=output_dir,
            model=request.model,
            num_images=request.num_images,
            width=request.width,
            height=request.height
        )
        
        return {
            "success": True,
            "model": request.model,
            "image_count": len(image_paths),
            "images": [
                {
                    "path": path,
                    "url": f"/images/file?path={path}"
                }
                for path in image_paths
            ]
        }
    except Exception as e:
        logger.error(f"Error generating images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/file", tags=["Images"])
async def get_image_file(path: str = Query(..., description="Image file path")):
    """
    Download generated image file
    
    Returns the actual image file for viewing/downloading.
    """
    try:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        return FileResponse(path, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/generate-prompt", tags=["Images"])
async def create_image_prompt(summary: str = Body(..., embed=True)):
    """
    Generate an AI image prompt from test summary
    
    Converts personality analysis text into a detailed image generation prompt.
    """
    try:
        prompt = generate_image_prompt(summary)
        
        return {
            "success": True,
            "prompt": prompt,
            "length": len(prompt)
        }
    except Exception as e:
        logger.error(f"Error generating image prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PACKAGE MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/packages/purchase", tags=["Packages"])
async def purchase_package(request: PackagePurchase):
    """
    Purchase a test package
    
    Creates a package purchase record and links tests to the user.
    """
    try:
        # Record package purchase
        user_package_id = db.purchase_package(request.chat_id, request.package_id)
        
        # Add tests to package
        db.add_package_tests(user_package_id, request.test_ids)
        
        return {
            "success": True,
            "message": "Package purchased successfully",
            "user_package_id": user_package_id,
            "test_count": len(request.test_ids)
        }
    except Exception as e:
        logger.error(f"Error purchasing package: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/packages/{chat_id}", tags=["Packages"])
async def get_user_packages(chat_id: int):
    """
    Get all packages purchased by a user
    
    Returns list of package purchases with completion status.
    """
    try:
        packages = db.get_user_packages(chat_id)
        
        result = []
        for pkg in packages:
            tests = db.get_package_tests(pkg['id'])
            result.append({
                "id": pkg['id'],
                "package_id": pkg['package_id'],
                "purchase_timestamp": pkg['purchase_timestamp'],
                "completed": bool(pkg['completed']),
                "tests": [dict(t) for t in tests]
            })
        
        return {
            "success": True,
            "chat_id": chat_id,
            "package_count": len(result),
            "packages": result
        }
    except Exception as e:
        logger.error(f"Error getting packages for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/packages/{chat_id}/{user_package_id}", tags=["Packages"])
async def get_package_details(chat_id: int, user_package_id: int):
    """
    Get detailed information about a specific package
    
    Returns package info with test completion status.
    """
    try:
        package = db.get_user_package(user_package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        if package['chat_id'] != chat_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        tests = db.get_package_tests(user_package_id)
        
        return {
            "success": True,
            "package": dict(package),
            "tests": [dict(t) for t in tests]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting package {user_package_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/packages/{user_package_id}/tests/{package_test_id}/complete", tags=["Packages"])
async def mark_package_test_complete(user_package_id: int, package_test_id: int):
    """
    Mark a test in a package as completed
    
    Updates test completion status and checks if entire package is finished.
    """
    try:
        success = db.mark_package_test_completed(package_test_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to mark test as completed")
        
        # Check package completion status
        package = db.get_user_package(user_package_id)
        
        return {
            "success": True,
            "message": "Test marked as completed",
            "package_completed": bool(package['completed']) if package else False
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking test complete: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.get("/admin/users", tags=["Admin"])
async def list_all_users():
    """
    List all registered users (Admin only)
    
    Returns complete user list with statistics.
    """
    try:
        users = db.get_all_users()
        
        return {
            "success": True,
            "total_users": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Error listing all users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/stats", tags=["Admin"])
async def get_system_statistics():
    """
    Get system-wide statistics (Admin only)
    
    Returns aggregated metrics about users, tests, and usage.
    """
    try:
        users = db.get_all_users()
        
        # Aggregate statistics
        total_balance = sum(u.get('balance', 0) for u in users)
        total_tests = 0
        
        for user in users:
            tests = db.get_user_tests(user['chat_id'])
            total_tests += len(tests)
        
        return {
            "success": True,
            "statistics": {
                "total_users": len(users),
                "total_tests_taken": total_tests,
                "total_balance": total_balance,
                "average_tests_per_user": round(total_tests / len(users), 2) if users else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PROFILE AI UPDATE ENDPOINT
# ============================================================================

@app.post("/users/{chat_id}/profile/ai-update", tags=["Users", "AI"])
async def ai_update_profile(
    chat_id: int,
    test_result_text: str = Body(..., embed=True, description="Test result text to integrate into profile")
):
    """
    Update user profile using AI analysis
    
    Uses AI to intelligently merge test results into the user's profile.
    """
    try:
        update_user_profile_with_ai(chat_id, test_result_text)
        
        # Get updated profile
        user_data = db.get_user(chat_id)
        
        return {
            "success": True,
            "message": "Profile updated with AI analysis",
            "updated_profile": user_data.get("information", "")
        }
    except Exception as e:
        logger.error(f"Error in AI profile update for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# APPLICATION STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Blue Psychology Test API starting up...")
    
    # Initialize session storage
    app.test_sessions = {}
    
    # Pre-warm smart chat components
    try:
        get_smart_chat_agent()
        logger.info("✅ Smart chat agent initialized")
    except Exception as e:
        logger.warning(f"⚠️ Smart chat initialization deferred: {e}")
    
    logger.info("✅ API ready to accept requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Blue Psychology Test API shutting down...")
    
    # Clear session storage
    if hasattr(app, 'test_sessions'):
        app.test_sessions.clear()
    
    logger.info("✅ Cleanup complete")

# ============================================================================
# RUN SERVER (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
