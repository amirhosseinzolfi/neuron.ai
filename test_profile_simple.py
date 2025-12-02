import requests
import json

BASE_URL = "http://localhost:15801"

print("=== Profile Extractor API Test ===\n")

# Test 1: Create profile
print("1. Creating profile for user_456...")
response = requests.post(
    f"{BASE_URL}/profile/process",
    data={
        "user_id": "user_456",
        "message": "Hi! I'm Sarah Chen, 32 years old. I work as a data scientist at Google. I enjoy machine learning, yoga, and traveling to Japan."
    }
)
print(f"✓ Profile created - Confidence: {response.json()['confidence']}")
print(f"  Name: {response.json()['profile']['name']}")
print(f"  Age: {response.json()['profile']['age']}")
print(f"  Occupation: {response.json()['profile']['occupation']}")
print(f"  Interests: {', '.join(response.json()['profile']['interests'])}\n")

# Test 2: Get profile
print("2. Retrieving profile...")
response = requests.get(f"{BASE_URL}/profile/user_456")
print(f"✓ Profile retrieved\n")

# Test 3: Update profile
print("3. Updating profile with new info...")
response = requests.post(
    f"{BASE_URL}/profile/process",
    data={
        "user_id": "user_456",
        "message": "I also love photography and my email is sarah.chen@example.com"
    }
)
print(f"✓ Profile updated - Action: {response.json()['action']}")
print(f"  Updated interests: {', '.join(response.json()['profile']['interests'])}")
print(f"  Email: {response.json()['profile']['contact']['email']}\n")

# Test 4: Stats
print("4. Getting profile stats...")
response = requests.get(f"{BASE_URL}/profile/user_456/stats")
stats = response.json()
print(f"✓ Stats retrieved")
print(f"  Completeness: {stats['data_completeness']:.1f}%")
print(f"  Interests count: {stats['interests_count']}\n")

# Test 5: List all
print("5. Listing all profiles...")
response = requests.get(f"{BASE_URL}/profile/list")
print(f"✓ Total profiles: {response.json()['total_profiles']}\n")

print("=== All tests passed! ===")
