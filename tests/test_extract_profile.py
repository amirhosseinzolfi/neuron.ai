#!/usr/bin/env python3
"""
Test script for AI-powered profile extraction functionality.

Tests the refactored update_user_profile_with_ai function with:
- Clean modular architecture
- FastAPI profile extractor integration
- Comprehensive logging and debugging
- Multiple test scenarios
"""

import sys
import json
import time
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Import the refactored function
from ai_utils import update_user_profile_with_ai
import db


console = Console()


def setup_test_user(chat_id: int) -> Dict:
    """Create or reset test user with initial profile."""
    console.rule(f"[bold cyan]🔧 Setup Test User: {chat_id}", style="cyan")
    
    # Ensure user exists
    existing = db.get_user(chat_id)
    if not existing:
        db.add_user(
            chat_id=chat_id,
            name=f"TestUser_{chat_id}",
            progress=0
        )
        console.log(f"[green]✅ Created new test user: {chat_id}[/green]")
    else:
        console.log(f"[yellow]📝 Using existing user: {chat_id}[/yellow]")
    
    # Create initial profile
    initial_profile = {
        "core_info": {
            "name": "Alice",
            "age": 28,
            "occupation": "Software Engineer"
        },
        "professional_profile": {
            "career_summary": "5 years in software development",
            "skills": ["Python", "JavaScript", "React"],
            "job_history": []
        },
        "social_profile": {
            "relationship_status": "Single",
            "relations": []
        },
        "lifestyle": {
            "summary": "Active lifestyle with focus on technology and fitness",
            "routines": ["Morning exercise", "Evening coding"]
        },
        "personal_outlook": {
            "interests": ["Programming", "Hiking", "Reading"],
            "goals": ["Learn AI/ML", "Travel to Japan"],
            "values": ["Innovation", "Continuous learning"]
        },
        "psychological_profile": {
            "summary": "Analytical thinker with creative problem-solving approach",
            "personality_traits": {
                "openness": 0.8,
                "conscientiousness": 0.7,
                "extraversion": 0.5,
                "agreeableness": 0.6,
                "neuroticism": 0.3
            },
            "cognitive_biases": [],
            "strengths": ["Logical thinking", "Attention to detail"],
            "areas_for_development": ["Work-life balance", "Public speaking"]
        },
        "psychological_tests": [],
        "additional_data": {},
        "metadata": {
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "confidence": 0.75,
            "extracted_from": ["initial_setup"]
        }
    }
    
    # Save initial profile
    profile_json = json.dumps(initial_profile, ensure_ascii=False)
    db.save_user_profile(chat_id, profile_json)
    console.log(f"[green]✅ Saved initial profile ({len(profile_json)} chars)[/green]")
    
    return initial_profile


def display_test_header(test_num: int, title: str, description: str):
    """Display test header."""
    console.rule(f"[bold blue]Test {test_num}: {title}", style="blue")
    console.print(Panel(
        Text(description, style="white"),
        title=f"Test {test_num} Description",
        border_style="blue"
    ))


def display_test_result(success: bool, duration: float):
    """Display test result."""
    status = "✅ PASSED" if success else "❌ FAILED"
    color = "green" if success else "red"
    console.print(Panel(
        Text(f"{status}\nDuration: {duration:.2f}s", style=color),
        title="Test Result",
        border_style=color
    ))


def test_basic_profile_update():
    """Test basic profile update with simple test results."""
    test_num = 1
    display_test_header(
        test_num,
        "Basic Profile Update",
        "Update profile with simple psychology test results"
    )
    
    chat_id = 999001
    setup_test_user(chat_id)
    
    # Prepare test data
    test_result = """
Psychology Test Results - MBTI Assessment

User: Alice
Result: INTJ (Introverted, Intuitive, Thinking, Judging)

Personality Analysis:
- Strategic thinker with strong analytical skills
- Prefers working independently
- Values competence and knowledge
- Organized and goal-oriented
- May struggle with emotional expression

Strengths:
- Problem-solving ability
- Strategic planning
- Independent work
- Logical reasoning

Development Areas:
- Emotional intelligence
- Team collaboration
- Flexibility with changes
- Social networking
"""
    
    conversation_history = [
        {"role": "assistant", "content": "سلام! به تست شخصیت‌شناسی MBTI خوش آمدید."},
        {"role": "user", "content": "سلام، من علاقه‌مند به شرکت در تست هستم."},
        {"role": "assistant", "content": "آیا شما فردی درون‌گرا یا برون‌گرا هستید؟"},
        {"role": "user", "content": "من درون‌گرا هستم و ترجیح می‌دهم به تنهایی کار کنم."},
    ]
    
    state = {
        "history_summary": "کاربر در تست MBTI شرکت کرد و نتیجه INTJ دریافت کرد.",
        "user_info": "نام: Alice، سن: 28، شغل: مهندس نرم‌افزار"
    }
    
    # Run test
    start_time = time.time()
    success = update_user_profile_with_ai(
        chat_id=chat_id,
        test_result_text=test_result,
        conversation_history=conversation_history,
        state=state
    )
    duration = time.time() - start_time
    
    display_test_result(success, duration)
    return success


def test_comprehensive_profile_update():
    """Test comprehensive profile update with detailed test results."""
    test_num = 2
    display_test_header(
        test_num,
        "Comprehensive Profile Update",
        "Update profile with detailed Big Five personality test results"
    )
    
    chat_id = 999002
    setup_test_user(chat_id)
    
    # Prepare comprehensive test data
    test_result = """
Big Five Personality Assessment - Detailed Results

User: Alice Johnson
Age: 28
Occupation: Software Engineer

Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Openness to Experience: 85/100 (Very High)
   - Intellectually curious and creative
   - Enjoys exploring new ideas and concepts
   - Appreciates art, literature, and abstract thinking
   - Open to unconventional approaches

2. Conscientiousness: 78/100 (High)
   - Well-organized and detail-oriented
   - Follows through on commitments
   - Plans ahead and sets clear goals
   - May sometimes be perfectionistic

3. Extraversion: 42/100 (Low-Moderate)
   - Prefers smaller social groups
   - Enjoys one-on-one conversations
   - Values alone time for reflection
   - Can be assertive when necessary

4. Agreeableness: 65/100 (Moderate-High)
   - Generally cooperative and empathetic
   - Values harmony in relationships
   - Can be diplomatic in conflicts
   - Balances own needs with others'

5. Neuroticism: 38/100 (Low-Moderate)
   - Generally emotionally stable
   - Handles stress reasonably well
   - Occasional anxiety in new situations
   - Good emotional regulation

Cognitive Patterns:
- Systematic problem-solving approach
- Strong analytical thinking
- Pattern recognition ability
- Preference for evidence-based decisions
- Slight confirmation bias tendency

Strengths Identified:
✓ Excellent technical problem-solving
✓ Strategic thinking and planning
✓ Creativity in approach to challenges
✓ Strong focus and concentration
✓ Adaptability to new technologies
✓ Reliability and dependability

Areas for Development:
• Emotional expression and vulnerability
• Delegation of tasks to others
• Work-life balance maintenance
• Building broader social networks
• Handling unexpected changes
• Public speaking confidence

Behavioral Insights:
- Thrives in autonomous work environments
- Benefits from clear structure and expectations
- Values continuous learning and growth
- Motivated by intellectual challenges
- May struggle with ambiguous situations

Recommendations:
1. Pursue leadership training to develop delegation skills
2. Practice mindfulness for stress management
3. Join professional networking groups
4. Set boundaries between work and personal time
5. Consider public speaking workshops

Overall Assessment:
Alice demonstrates a strong profile for analytical and creative work. Her high openness and conscientiousness, combined with moderate extraversion, make her well-suited for independent technical roles with occasional collaboration. Focus on developing interpersonal skills and work-life balance will enhance overall well-being and career growth.
"""
    
    conversation_history = [
        {"role": "assistant", "content": "Welcome to the Big Five Personality Assessment."},
        {"role": "user", "content": "Hi, I'm excited to understand my personality better."},
        {"role": "assistant", "content": "Let's start. How do you typically spend your free time?"},
        {"role": "user", "content": "I enjoy reading technical books, hiking in nature, and working on personal coding projects."},
        {"role": "assistant", "content": "Do you prefer working alone or in teams?"},
        {"role": "user", "content": "I work best independently but can collaborate when needed. I value deep focus time."},
        {"role": "assistant", "content": "How do you handle stressful situations at work?"},
        {"role": "user", "content": "I try to stay calm and analyze the problem systematically. Sometimes I feel anxious initially but then focus on solutions."},
        {"role": "assistant", "content": "What are your long-term career goals?"},
        {"role": "user", "content": "I want to become an AI/ML expert and eventually lead innovative tech projects. I also want to maintain good work-life balance."},
    ]
    
    state = {
        "history_summary": "User completed comprehensive Big Five personality assessment showing high openness (85%), high conscientiousness (78%), moderate-low extraversion (42%), moderate-high agreeableness (65%), and low-moderate neuroticism (38%). Demonstrated strong analytical skills, creativity, and preference for independent work.",
        "user_info": "Name: Alice Johnson, Age: 28, Occupation: Software Engineer, Interests: Reading, Hiking, Coding, Goals: AI/ML expertise, Tech leadership, Work-life balance",
        "conversation_history": conversation_history
    }
    
    # Run test
    start_time = time.time()
    success = update_user_profile_with_ai(
        chat_id=chat_id,
        test_result_text=test_result,
        conversation_history=conversation_history,
        state=state
    )
    duration = time.time() - start_time
    
    display_test_result(success, duration)
    return success


def test_profile_merge_with_minimal_data():
    """Test profile update with minimal new data."""
    test_num = 3
    display_test_header(
        test_num,
        "Minimal Data Update",
        "Test profile merge when only small amount of new information is provided"
    )
    
    chat_id = 999003
    setup_test_user(chat_id)
    
    # Minimal test data
    test_result = """
Brief Stress Assessment

Result: Moderate stress levels detected
Recommendation: Practice relaxation techniques
"""
    
    conversation_history = [
        {"role": "assistant", "content": "How stressed do you feel on a scale of 1-10?"},
        {"role": "user", "content": "Around 6 - manageable but noticeable."},
    ]
    
    state = {
        "history_summary": "User reported moderate stress levels (6/10).",
        "user_info": ""
    }
    
    # Run test
    start_time = time.time()
    success = update_user_profile_with_ai(
        chat_id=chat_id,
        test_result_text=test_result,
        conversation_history=conversation_history,
        state=state
    )
    duration = time.time() - start_time
    
    display_test_result(success, duration)
    return success


def test_empty_profile_creation():
    """Test creating profile from scratch with no existing data."""
    test_num = 4
    display_test_header(
        test_num,
        "New Profile Creation",
        "Create comprehensive profile from scratch with no existing data"
    )
    
    chat_id = 999004
    
    # Create user but don't set profile
    existing = db.get_user(chat_id)
    if not existing:
        db.add_user(
            chat_id=chat_id,
            name=f"NewUser_{chat_id}",
            progress=0
        )
    
    console.log("[blue]📝 Starting with empty profile[/blue]")
    
    # Comprehensive test data for new profile
    test_result = """
Complete Psychological Profile Assessment

Name: Bob Smith
Age: 35
Occupation: Data Scientist

Big Five Results:
- Openness: 72%
- Conscientiousness: 88%
- Extraversion: 58%
- Agreeableness: 70%
- Neuroticism: 25%

Interests: Machine Learning, Data Visualization, Basketball, Photography
Goals: Publish research papers, Build ML startup, Learn Japanese
Values: Innovation, Teamwork, Work-life balance

Strengths:
- Data analysis expertise
- Clear communication
- Collaborative mindset
- Quick learner

Development Areas:
- Time management
- Saying no to commitments
- Imposter syndrome
"""
    
    conversation_history = [
        {"role": "user", "content": "My name is Bob Smith, I'm 35 and work as a data scientist."},
        {"role": "user", "content": "I love working with machine learning and creating data visualizations."},
        {"role": "user", "content": "In my free time, I play basketball and do photography."},
        {"role": "user", "content": "My goal is to publish research and eventually start my own ML company."},
        {"role": "user", "content": "I value innovation and teamwork, and I'm trying to maintain better work-life balance."},
    ]
    
    state = {
        "history_summary": "New user Bob Smith completed comprehensive psychological assessment.",
        "user_info": "Name: Bob Smith, Age: 35, Occupation: Data Scientist"
    }
    
    # Run test
    start_time = time.time()
    success = update_user_profile_with_ai(
        chat_id=chat_id,
        test_result_text=test_result,
        conversation_history=conversation_history,
        state=state
    )
    duration = time.time() - start_time
    
    display_test_result(success, duration)
    return success


def verify_profile_in_database(chat_id: int):
    """Verify that profile was saved correctly to database."""
    console.rule("[bold cyan]🔍 Database Verification", style="cyan")
    
    profile_json = db.get_user_profile(chat_id)
    
    if not profile_json:
        console.log(f"[red]❌ No profile found in database for chat_id: {chat_id}[/red]")
        return False
    
    try:
        profile = json.loads(profile_json)
        
        table = Table(title=f"Profile in Database - Chat ID: {chat_id}", 
                     show_header=True, header_style="bold cyan")
        table.add_column("Field", style="yellow")
        table.add_column("Value", style="white")
        
        # Check core fields
        core_info = profile.get("core_info", {})
        table.add_row("Name", str(core_info.get("name", "N/A")))
        table.add_row("Age", str(core_info.get("age", "N/A")))
        table.add_row("Occupation", str(core_info.get("occupation", "N/A")))
        
        # Check metadata
        metadata = profile.get("metadata", {})
        table.add_row("Confidence", f"{metadata.get('confidence', 0.0):.2f}")
        table.add_row("Last Updated", str(metadata.get("last_updated", "N/A")))
        
        # Check profile size
        table.add_row("JSON Size", f"{len(profile_json)} chars")
        table.add_row("Top-level Keys", ", ".join(profile.keys()))
        
        console.print(table)
        console.log("[green]✅ Profile verified in database[/green]")
        return True
        
    except json.JSONDecodeError as e:
        console.log(f"[red]❌ Invalid JSON in database: {e}[/red]")
        return False


def run_all_tests():
    """Run all test scenarios."""
    console.rule("[bold magenta]🧪 Profile Extraction Test Suite", style="magenta")
    console.print(Panel(
        Text("Testing refactored AI-powered profile extraction functionality", style="white"),
        title="Test Suite Info",
        border_style="magenta"
    ))
    
    results = []
    
    # Run tests
    console.print("\n")
    results.append(("Test 1: Basic Profile Update", test_basic_profile_update()))
    
    console.print("\n")
    results.append(("Test 2: Comprehensive Update", test_comprehensive_profile_update()))
    
    console.print("\n")
    results.append(("Test 3: Minimal Data Update", test_profile_merge_with_minimal_data()))
    
    console.print("\n")
    results.append(("Test 4: New Profile Creation", test_empty_profile_creation()))
    
    # Verify database for one test
    console.print("\n")
    verify_profile_in_database(999002)
    
    # Summary
    console.print("\n")
    console.rule("[bold magenta]📊 Test Summary", style="magenta")
    
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Test", style="cyan")
    summary_table.add_column("Result", style="white")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        color = "green" if success else "red"
        summary_table.add_row(test_name, f"[{color}]{status}[/{color}]")
        if success:
            passed += 1
    
    console.print(summary_table)
    
    overall = f"{passed}/{len(results)} tests passed"
    overall_color = "green" if passed == len(results) else "yellow" if passed > 0 else "red"
    console.print(Panel(
        Text(overall, style=overall_color),
        title="Overall Result",
        border_style=overall_color
    ))


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Test suite failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
