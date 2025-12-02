"""Test profile extractor integration"""
import sys
sys.path.insert(0, '/root/blue-psychology-test')

from app.services.profile_client import extract_profile, save_user_profile, load_user_profile

print("=== Testing Profile Extractor Integration ===\n")

# Test 1: Extract profile from conversation
print("1. Extracting profile from conversation...")
conversation = [
    {"role": "assistant", "content": "Please provide your name and age"},
    {"role": "user", "content": "My name is Ali and I'm 25 years old"},
    {"role": "assistant", "content": "Please tell me about yourself"},
    {"role": "user", "content": "I work as a software engineer and love programming and gaming"}
]

result = extract_profile(
    user_id="test_user_123",
    messages=["My name is Ali and I'm 25 years old", "I work as a software engineer and love programming and gaming"],
    conversation_history=conversation
)

if result:
    print("✓ Profile extracted successfully")
    profile = result["profile"]
    print(f"  Name: {profile.get('name')}")
    print(f"  Age: {profile.get('age')}")
    print(f"  Occupation: {profile.get('occupation')}")
    print(f"  Interests: {profile.get('interests')}")
    print(f"  Confidence: {result.get('confidence')}")
    
    # Test 2: Save profile
    print("\n2. Saving profile...")
    if save_user_profile("test_user_123", profile):
        print("✓ Profile saved successfully")
    
    # Test 3: Load profile
    print("\n3. Loading profile...")
    loaded = load_user_profile("test_user_123")
    if loaded:
        print("✓ Profile loaded successfully")
        print(f"  Loaded name: {loaded.get('name')}")
    
    # Test 4: Refine profile
    print("\n4. Refining profile with new info...")
    result2 = extract_profile(
        user_id="test_user_123",
        messages=["I also enjoy reading books and my email is ali@example.com"],
        existing_profile=loaded
    )
    
    if result2:
        print("✓ Profile refined successfully")
        print(f"  Action: {result2.get('action')}")
        print(f"  Updated interests: {result2['profile'].get('interests')}")
        print(f"  Email: {result2['profile'].get('contact', {}).get('email')}")
else:
    print("✗ Profile extraction failed")

print("\n=== Test Complete ===")
