#!/usr/bin/env python3
"""
Test script for profile extractor with multimodal inputs
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ai_utils import extract_user_profile
from rich.console import Console

console = Console()

def create_test_media():
    """Create dummy test media files"""
    test_dir = Path("test_media")
    test_dir.mkdir(exist_ok=True)
    
    # Create dummy image (1x1 PNG)
    img_path = test_dir / "test_image.jpg"
    if not img_path.exists():
        # Minimal valid JPEG
        img_data = bytes.fromhex('ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232ffc00011080001000103012200021101031101ffc4001500010100000000000000000000000000000007ffc40014100100000000000000000000000000000000ffda000c03010002110311003f00bf800fffd9')
        img_path.write_bytes(img_data)
    
    # Create dummy audio (minimal OGG)
    audio_path = test_dir / "test_audio.ogg"
    if not audio_path.exists():
        # Minimal valid OGG Vorbis header
        audio_data = bytes.fromhex('4f676753000200000000000000000000000000000000000000001e01')
        audio_path.write_bytes(audio_data)
    
    return str(img_path), str(audio_path)

def test_text_only():
    """Test 1: Text-only profile extraction"""
    console.rule("[bold blue]Test 1: Text-Only Profile Extraction")
    
    result = extract_user_profile(
        user_id=999001,
        question1_text="علی 25 ساله هستم",
        question2_text="من یک برنامه نویس هستم و به موسیقی علاقه دارم"
    )
    
    if result:
        console.print("[green]✅ Test 1 PASSED[/green]")
        return True
    else:
        console.print("[red]❌ Test 1 FAILED[/red]")
        return False

def test_with_image():
    """Test 2: Text + Image"""
    console.rule("[bold blue]Test 2: Text + Image Profile Extraction")
    
    img_path, _ = create_test_media()
    
    result = extract_user_profile(
        user_id=999002,
        question1_text="سارا 30 ساله",
        question1_media=[{'type': 'image', 'path': img_path}],
        question2_text="من معلم هستم"
    )
    
    if result:
        console.print("[green]✅ Test 2 PASSED[/green]")
        return True
    else:
        console.print("[red]❌ Test 2 FAILED[/red]")
        return False

def test_with_audio():
    """Test 3: Text + Audio"""
    console.rule("[bold blue]Test 3: Text + Audio Profile Extraction")
    
    _, audio_path = create_test_media()
    
    result = extract_user_profile(
        user_id=999003,
        question1_text="رضا 28 ساله",
        question2_text="من دانشجو هستم",
        question2_media=[{'type': 'audio', 'path': audio_path}]
    )
    
    if result:
        console.print("[green]✅ Test 3 PASSED[/green]")
        return True
    else:
        console.print("[red]❌ Test 3 FAILED[/red]")
        return False

def test_multimodal_full():
    """Test 4: Full multimodal (text + image + audio)"""
    console.rule("[bold blue]Test 4: Full Multimodal Profile Extraction")
    
    img_path, audio_path = create_test_media()
    
    result = extract_user_profile(
        user_id=999004,
        question1_text="مریم 26 ساله",
        question1_media=[
            {'type': 'image', 'path': img_path},
            {'type': 'audio', 'path': audio_path}
        ],
        question2_text="من طراح گرافیک هستم و به هنر علاقه دارم",
        question2_media=[{'type': 'image', 'path': img_path}]
    )
    
    if result:
        console.print("[green]✅ Test 4 PASSED[/green]")
        return True
    else:
        console.print("[red]❌ Test 4 FAILED[/red]")
        return False

def test_missing_media():
    """Test 5: Handle missing media gracefully"""
    console.rule("[bold blue]Test 5: Missing Media Fallback")
    
    result = extract_user_profile(
        user_id=999005,
        question1_text="احمد 35 ساله",
        question1_media=[{'type': 'image', 'path': '/nonexistent/file.jpg'}],
        question2_text="من پزشک هستم"
    )
    
    if result:
        console.print("[green]✅ Test 5 PASSED (fallback to text-only)[/green]")
        return True
    else:
        console.print("[red]❌ Test 5 FAILED[/red]")
        return False

def main():
    console.print("[bold cyan]🧪 Profile Extractor Test Suite[/bold cyan]\n")
    
    # Check if API is running
    try:
        import requests
        response = requests.get("http://localhost:15800/health", timeout=2)
        if response.status_code != 200:
            console.print("[red]❌ Profile API not responding at http://localhost:15800[/red]")
            console.print("[yellow]Please start the profile extractor API first[/yellow]")
            return
    except Exception as e:
        console.print(f"[red]❌ Cannot connect to API: {e}[/red]")
        console.print("[yellow]Please start the profile extractor API at http://localhost:15800[/yellow]")
        return
    
    results = []
    
    # Run tests
    results.append(("Text-Only", test_text_only()))
    results.append(("Text + Image", test_with_image()))
    results.append(("Text + Audio", test_with_audio()))
    results.append(("Full Multimodal", test_multimodal_full()))
    results.append(("Missing Media Fallback", test_missing_media()))
    
    # Summary
    console.rule("[bold magenta]Test Summary")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        console.print(f"{status} - {name}")
    
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("[bold green]🎉 All tests passed![/bold green]")
    else:
        console.print("[bold red]⚠️  Some tests failed[/bold red]")

if __name__ == "__main__":
    main()
