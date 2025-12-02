"""
Example Python Client for Blue Psychology Test API

This script demonstrates how to interact with the API programmatically.
"""

import requests
import json
import time
from typing import Dict, Any, Optional


class PsychologyTestClient:
    """Client for interacting with the Psychology Test API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    def create_user(self, chat_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Create or update a user"""
        response = self.session.post(
            f"{self.base_url}/users",
            json={
                "chat_id": chat_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_user(self, chat_id: int) -> Dict[str, Any]:
        """Get user profile"""
        response = self.session.get(f"{self.base_url}/users/{chat_id}")
        response.raise_for_status()
        return response.json()
    
    def update_profile(self, chat_id: int, **kwargs) -> Dict[str, Any]:
        """Update user profile"""
        response = self.session.patch(
            f"{self.base_url}/users/{chat_id}/profile",
            json=kwargs
        )
        response.raise_for_status()
        return response.json()
    
    def get_balance(self, chat_id: int) -> int:
        """Get user balance"""
        response = self.session.get(f"{self.base_url}/users/{chat_id}/balance")
        response.raise_for_status()
        return response.json()["balance"]
    
    def update_balance(self, chat_id: int, amount: int) -> Dict[str, Any]:
        """Update user balance"""
        response = self.session.post(
            f"{self.base_url}/users/balance",
            json={"chat_id": chat_id, "amount": amount}
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # TEST MANAGEMENT
    # =========================================================================
    
    def list_tests(self) -> Dict[str, Any]:
        """List all available tests"""
        response = self.session.get(f"{self.base_url}/tests")
        response.raise_for_status()
        return response.json()
    
    def get_test(self, test_id: int) -> Dict[str, Any]:
        """Get test details"""
        response = self.session.get(f"{self.base_url}/tests/{test_id}")
        response.raise_for_status()
        return response.json()
    
    def initialize_test(self, user_name: str, age: int, user_info: str = "",
                       test_type: str = "1", chat_id: int = None) -> Dict[str, Any]:
        """Start a new test session"""
        response = self.session.post(
            f"{self.base_url}/tests/initialize",
            json={
                "user_name": user_name,
                "age": age,
                "user_info": user_info,
                "test_type": test_type,
                "chat_id": chat_id
            }
        )
        response.raise_for_status()
        return response.json()
    
    def submit_answer(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """Submit an answer to a test question"""
        response = self.session.post(
            f"{self.base_url}/tests/answer",
            json={
                "session_id": session_id,
                "user_input": user_input
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_test_history(self, chat_id: int) -> Dict[str, Any]:
        """Get user's test history"""
        response = self.session.get(f"{self.base_url}/users/{chat_id}/tests")
        response.raise_for_status()
        return response.json()
    
    def get_test_result(self, chat_id: int, result_id: int) -> Dict[str, Any]:
        """Get specific test result"""
        response = self.session.get(
            f"{self.base_url}/users/{chat_id}/tests/{result_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def download_test_pdf(self, chat_id: int, result_id: int, 
                         output_path: str) -> None:
        """Download test result PDF"""
        response = self.session.get(
            f"{self.base_url}/users/{chat_id}/tests/{result_id}/pdf",
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    # =========================================================================
    # SMART CHAT
    # =========================================================================
    
    def send_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Send message to AI chat"""
        response = self.session.post(
            f"{self.base_url}/chat",
            json={
                "user_id": user_id,
                "message": message
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_chat_history(self, user_id: str) -> Dict[str, Any]:
        """Get chat conversation history"""
        response = self.session.get(f"{self.base_url}/chat/{user_id}/history")
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # IMAGE GENERATION
    # =========================================================================
    
    def generate_images(self, prompt: str, user_name: str, model: str = "flux",
                       num_images: int = 1, width: int = 512, 
                       height: int = 512) -> Dict[str, Any]:
        """Generate personality images"""
        response = self.session.post(
            f"{self.base_url}/images/generate",
            json={
                "prompt": prompt,
                "user_name": user_name,
                "model": model,
                "num_images": num_images,
                "width": width,
                "height": height
            }
        )
        response.raise_for_status()
        return response.json()
    
    def download_image(self, path: str, output_path: str) -> None:
        """Download generated image"""
        response = self.session.get(
            f"{self.base_url}/images/file",
            params={"path": path},
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def generate_image_prompt(self, summary: str) -> str:
        """Generate image prompt from test summary"""
        response = self.session.post(
            f"{self.base_url}/images/generate-prompt",
            json={"summary": summary}
        )
        response.raise_for_status()
        return response.json()["prompt"]
    
    # =========================================================================
    # PACKAGES
    # =========================================================================
    
    def purchase_package(self, chat_id: int, package_id: str, 
                        test_ids: list) -> Dict[str, Any]:
        """Purchase a test package"""
        response = self.session.post(
            f"{self.base_url}/packages/purchase",
            json={
                "chat_id": chat_id,
                "package_id": package_id,
                "test_ids": test_ids
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_packages(self, chat_id: int) -> Dict[str, Any]:
        """Get user's packages"""
        response = self.session.get(f"{self.base_url}/packages/{chat_id}")
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def take_complete_test(self, chat_id: int, user_name: str, age: int,
                          test_type: str = "1", 
                          answer_callback=None) -> Dict[str, Any]:
        """
        Take a complete test interactively
        
        Args:
            chat_id: User's chat ID
            user_name: User's name
            age: User's age
            test_type: Test type/ID
            answer_callback: Function called for each question to get answer
                            If None, uses input()
        
        Returns:
            Final test results
        """
        # Initialize test
        init_result = self.initialize_test(
            user_name=user_name,
            age=age,
            test_type=test_type,
            chat_id=chat_id
        )
        
        session_id = init_result["session_id"]
        total_questions = init_result["total_questions"]
        
        print(f"Started test: {init_result['test_name']}")
        print(f"Total questions: {total_questions}\n")
        
        # Answer questions
        current_question = 1
        question_text = init_result["question_text"]
        
        while True:
            print(f"\n{question_text}\n")
            
            # Get answer
            if answer_callback:
                answer = answer_callback(current_question, question_text)
            else:
                answer = input("Your answer: ")
            
            # Submit answer
            result = self.submit_answer(session_id, answer)
            
            if result.get("finished"):
                print("\n✅ Test completed!")
                return result
            elif not result.get("success"):
                print(f"❌ Invalid answer: {result.get('retry_message')}")
            else:
                current_question = result["current_question"]
                question_text = result["question_text"]


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

def example_basic_usage():
    """Example: Basic API usage"""
    print("="*60)
    print("Example 1: Basic Usage")
    print("="*60)
    
    client = PsychologyTestClient()
    
    # Check API health
    health = client.health_check()
    print(f"API Status: {health['status']}")
    
    # Create user
    user_result = client.create_user(
        chat_id=12345,
        username="demo_user",
        first_name="Demo",
        last_name="User"
    )
    print(f"User created: {user_result['message']}")
    
    # Get user profile
    user_profile = client.get_user(12345)
    print(f"User balance: {user_profile['user']['balance']}")
    
    # List available tests
    tests = client.list_tests()
    print(f"\nAvailable tests: {tests['count']}")
    for i, test in enumerate(tests['tests'], 1):
        print(f"  {i}. {test['test_name']}")


def example_complete_test():
    """Example: Taking a complete test"""
    print("\n" + "="*60)
    print("Example 2: Complete Test")
    print("="*60)
    
    client = PsychologyTestClient()
    
    # Predefined answers for demonstration
    answers = ["گزینه اول", "بله", "خیر", "گاهی اوقات", "همیشه"]
    answer_index = 0
    
    def auto_answer(question_num, question_text):
        nonlocal answer_index
        answer = answers[answer_index % len(answers)]
        answer_index += 1
        print(f"Auto-answering: {answer}")
        time.sleep(0.5)  # Simulate thinking
        return answer
    
    # Take test
    result = client.take_complete_test(
        chat_id=12345,
        user_name="Demo User",
        age=25,
        test_type="1",
        answer_callback=auto_answer
    )
    
    print("\n📊 Test Results:")
    print(result['summary'][:500] + "...")


def example_smart_chat():
    """Example: Using smart chat"""
    print("\n" + "="*60)
    print("Example 3: Smart Chat")
    print("="*60)
    
    client = PsychologyTestClient()
    user_id = "demo_user_001"
    
    messages = [
        "سلام، چطور می‌توانید به من کمک کنید؟",
        "احساس استرس می‌کنم",
        "چطور می‌توانم آرامش پیدا کنم؟"
    ]
    
    for msg in messages:
        print(f"\n👤 You: {msg}")
        response = client.send_message(user_id, msg)
        print(f"🤖 AI: {response['response'][:200]}...")
        time.sleep(1)
    
    # Get conversation history
    history = client.get_chat_history(user_id)
    print(f"\n📜 Total messages in conversation: {history['message_count']}")


def example_image_generation():
    """Example: Generating personality images"""
    print("\n" + "="*60)
    print("Example 4: Image Generation")
    print("="*60)
    
    client = PsychologyTestClient()
    
    # Test summary
    summary = """
    شما فردی درون‌گرا و خلاق هستید که به تفکر عمیق و تحلیل علاقه دارید.
    رنگ‌های آبی و بنفش با شخصیت شما همخوانی دارند.
    """
    
    # Generate image prompt
    print("🎨 Generating image prompt...")
    prompt = client.generate_image_prompt(summary)
    print(f"Generated prompt: {prompt[:100]}...")
    
    # Generate images
    print("\n🖼️ Generating images...")
    result = client.generate_images(
        prompt=prompt,
        user_name="demo_user",
        model="flux",
        num_images=1,
        width=512,
        height=512
    )
    
    print(f"Generated {result['image_count']} image(s)")
    
    # Download first image
    if result['images']:
        image_path = result['images'][0]['path']
        print(f"\n📥 Downloading image...")
        client.download_image(image_path, "demo_personality.png")
        print("✅ Saved as demo_personality.png")


def example_package_management():
    """Example: Managing test packages"""
    print("\n" + "="*60)
    print("Example 5: Package Management")
    print("="*60)
    
    client = PsychologyTestClient()
    chat_id = 12345
    
    # Check current balance
    balance = client.get_balance(chat_id)
    print(f"Current balance: {balance}")
    
    # Add credits
    if balance < 1000:
        client.update_balance(chat_id, 1000)
        print("Added 1000 credits")
    
    # Purchase package
    print("\n🛒 Purchasing package...")
    purchase_result = client.purchase_package(
        chat_id=chat_id,
        package_id="premium_bundle",
        test_ids=[1, 2, 3]
    )
    print(f"✅ Package purchased: {purchase_result['user_package_id']}")
    
    # Deduct cost
    client.update_balance(chat_id, -500)
    
    # Get packages
    packages = client.get_packages(chat_id)
    print(f"\n📦 Total packages: {packages['package_count']}")
    for pkg in packages['packages']:
        status = "✅ Completed" if pkg['completed'] else "⏳ In Progress"
        print(f"  - {pkg['package_id']}: {status} ({len(pkg['tests'])} tests)")


def run_all_examples():
    """Run all example functions"""
    try:
        example_basic_usage()
        # example_complete_test()  # Commented to avoid long test
        example_smart_chat()
        # example_image_generation()  # Commented as it takes time
        example_package_management()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run all examples
    run_all_examples()
    
    # Or run individual examples:
    # example_basic_usage()
    # example_smart_chat()
    # example_image_generation()
