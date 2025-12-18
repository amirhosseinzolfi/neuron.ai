#!/usr/bin/env python3
"""
Test script for profile update refactoring.
Verifies that the new profile system works correctly.
"""

import sys
import os
import json
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import db
from ai_utils import update_user_profile_with_ai

console = Console()

def test_api_connection():
    """Test if profile API is running"""
    console.rule("[bold cyan]Testing API Connection")
    
    try:
        response = requests.get("http://localhost:15800/health", timeout=5)
        if response.status_code == 200:
            console.print("✅ Profile API is running", style="green")
            return True
        else:
            console.print(f"⚠️ API returned status {response.status_code}", style="yellow")
            return False
    except Exception as e:
        console.print(f"❌ Cannot connect to API: {e}", style="red")
        console.print("💡 Start API with: ./start_full_api.sh", style="blue")
        return False


def test_profile_json_operations():
    """Test saving and loading profile JSON"""
    console.rule("[bold cyan]Testing Profile JSON Operations")
    
    test_chat_id = 999999  # Test user ID
    
    # Create test profile
    test_profile = {
        "user_id": str(test_chat_id),
        "name": "Test User",
        "age": 30,
        "occupation": "Software Tester",
        "interests": ["testing", "automation", "quality"],
        "bio": "A test profile for verification",
        "confidence": 0.95,
        "last_updated": "2025-11-05T12:00:00"
    }
    
    # Save profile
    try:
        profile_json = json.dumps(test_profile, ensure_ascii=False)
        db.save_user_profile(test_chat_id, profile_json)
        console.print(f"✅ Saved test profile for chat_id {test_chat_id}", style="green")
    except Exception as e:
        console.print(f"❌ Failed to save profile: {e}", style="red")
        return False
    
    # Load profile
    try:
        loaded_json = db.get_user_profile(test_chat_id)
        if loaded_json:
            loaded_profile = json.loads(loaded_json)
            console.print(f"✅ Loaded profile successfully", style="green")
            
            # Display loaded profile
            table = Table(title="Loaded Profile", show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in loaded_profile.items():
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                table.add_row(key, str(value))
            
            console.print(table)
            return True
        else:
            console.print("❌ Could not load profile", style="red")
            return False
    except Exception as e:
        console.print(f"❌ Failed to load profile: {e}", style="red")
        return False


def test_profile_update_with_api():
    """Test profile update with API"""
    console.rule("[bold cyan]Testing Profile Update with API")
    
    test_chat_id = 999999
    test_result_text = """
    Test Results Summary:
    
    The user shows strong analytical thinking and problem-solving skills.
    They demonstrate excellent attention to detail and systematic approach.
    Personality traits include: methodical, patient, detail-oriented.
    
    Recommended areas for growth: creative thinking, spontaneity, flexibility.
    """
    
    try:
        # Ensure test user exists
        db.get_or_create_user(test_chat_id, "Test", "User")
        
        console.print(f"📝 Updating profile for test user {test_chat_id}...", style="yellow")
        console.print("Test Result Text:", style="cyan")
        console.print(Panel(test_result_text, border_style="cyan"))
        
        # Call the update function
        update_user_profile_with_ai(test_chat_id, test_result_text)
        
        # Verify update
        updated_json = db.get_user_profile(test_chat_id)
        if updated_json:
            updated_profile = json.loads(updated_json)
            console.print("\n✅ Profile updated successfully!", style="green")
            
            # Show key fields
            table = Table(title="Updated Profile Key Fields", show_header=True)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Name", str(updated_profile.get("name", "N/A")))
            table.add_row("Age", str(updated_profile.get("age", "N/A")))
            table.add_row("Occupation", str(updated_profile.get("occupation", "N/A")))
            table.add_row("Interests", ", ".join(updated_profile.get("interests", [])))
            table.add_row("Confidence", f"{updated_profile.get('confidence', 0):.2f}")
            
            console.print(table)
            return True
        else:
            console.print("⚠️ Profile updated but could not verify", style="yellow")
            return False
            
    except Exception as e:
        console.print(f"❌ Profile update failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return False


def test_profile_display_formatting():
    """Test the profile display formatting function"""
    console.rule("[bold cyan]Testing Profile Display Formatting")
    
    from telegram_handlers import _format_profile_from_json
    
    test_profile = {
        "user_id": "999999",
        "name": "علی محمدی",
        "age": 28,
        "occupation": "برنامه‌نویس",
        "interests": ["برنامه‌نویسی", "ورزش", "مطالعه", "موسیقی"],
        "bio": "یک برنامه‌نویس با علاقه به هوش مصنوعی و روانشناسی. به دنبال یادگیری مداوم و رشد حرفه‌ای.",
        "contact": {
            "email": "ali@example.com"
        },
        "physical_attributes": {
            "hair_color": "مشکی",
            "eye_color": "قهوه‌ای"
        },
        "voice_profile": {
            "accent": "تهرانی",
            "tone": "رسمی"
        },
        "preferences": {
            "language": "Persian",
            "theme": "dark"
        },
        "confidence": 0.85,
        "last_updated": "2025-11-05T12:00:00"
    }
    
    test_user_data = {
        "first_name": "علی",
        "age": 28
    }
    
    try:
        formatted_text = _format_profile_from_json(test_profile, test_user_data)
        
        console.print("\n✅ Profile formatted successfully!", style="green")
        console.print("\nFormatted Profile Preview:", style="cyan")
        console.print(Panel(formatted_text, title="📱 Telegram Display", border_style="blue"))
        
        # Check length
        if len(formatted_text) <= 1200:
            console.print(f"✅ Length OK: {len(formatted_text)} chars (max 1200)", style="green")
        else:
            console.print(f"⚠️ Length warning: {len(formatted_text)} chars (max 1200)", style="yellow")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Formatting failed: {e}", style="red")
        import traceback
        console.print(traceback.format_exc(), style="red dim")
        return False


def cleanup_test_data():
    """Clean up test data"""
    console.rule("[bold cyan]Cleanup")
    
    test_chat_id = 999999
    
    try:
        # Note: We don't delete the user, just note that test data exists
        profile_json = db.get_user_profile(test_chat_id)
        if profile_json:
            console.print(f"ℹ️ Test profile remains in database for chat_id {test_chat_id}", style="blue")
            console.print("   You can manually delete it if needed", style="dim")
        
        return True
    except Exception as e:
        console.print(f"⚠️ Cleanup note: {e}", style="yellow")
        return True


def main():
    """Run all tests"""
    console.print(Panel.fit(
        "[bold blue]Profile Update Refactoring Test Suite[/bold blue]\n"
        "[cyan]Testing new JSON-based profile system[/cyan]",
        border_style="blue"
    ))
    
    results = {}
    
    # Test 1: API Connection
    results['api_connection'] = test_api_connection()
    
    # Test 2: Profile JSON Operations
    results['json_operations'] = test_profile_json_operations()
    
    # Test 3: Profile Display Formatting
    results['display_formatting'] = test_profile_display_formatting()
    
    # Test 4: Profile Update with API (only if API is available)
    if results['api_connection']:
        results['profile_update'] = test_profile_update_with_api()
    else:
        console.print("\n⚠️ Skipping profile update test (API not available)", style="yellow")
        results['profile_update'] = None
    
    # Cleanup
    cleanup_test_data()
    
    # Summary
    console.rule("[bold cyan]Test Summary")
    
    summary_table = Table(title="Test Results", show_header=True, header_style="bold")
    summary_table.add_column("Test", style="cyan")
    summary_table.add_column("Result", style="white")
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
            style = "green"
        elif result is False:
            status = "❌ FAIL"
            style = "red"
        else:
            status = "⏭️ SKIP"
            style = "yellow"
        
        summary_table.add_row(test_name.replace('_', ' ').title(), f"[{style}]{status}[/{style}]")
    
    console.print(summary_table)
    
    # Overall result
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    if passed == total and total > 0:
        console.print(f"\n🎉 All {passed}/{total} tests passed!", style="bold green")
        return 0
    elif passed > 0:
        console.print(f"\n⚠️ {passed}/{total} tests passed", style="bold yellow")
        return 1
    else:
        console.print(f"\n❌ {passed}/{total} tests passed", style="bold red")
        return 2


if __name__ == "__main__":
    sys.exit(main())
