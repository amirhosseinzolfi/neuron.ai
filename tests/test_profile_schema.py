"""
Test script for comprehensive profile extractor schema
Demonstrates usage of the enhanced profile system
"""

import json
import os
from datetime import datetime

# Import the profile extractor
from app.services.profile_extract_agent_json import (
    process_input,
    get_profile,
    get_profile_stats,
    delete_profile,
    list_profiles,
    UserProfile,
    PersonalityTraits,
    EmotionalProfile,
    GoalsAndAspirations
)


def test_basic_profile_creation():
    """Test creating a basic profile from text"""
    print("\n" + "="*60)
    print("TEST 1: Basic Profile Creation")
    print("="*60)
    
    user_id = "test_user_001"
    
    # Clean up any existing profile
    if os.path.exists(f"database/user_profiles/{user_id}_profile.json"):
        delete_profile(user_id)
    
    result = process_input(
        user_id=user_id,
        message="""I'm Sarah Johnson, 28 years old, a software engineer working in AI/ML.
        I love reading sci-fi novels, hiking in the mountains, and playing guitar.
        My short-term goal is to learn advanced machine learning, and long-term I want to 
        start my own AI consulting company. I'm an INTJ personality type and identify as 
        an introvert who values deep, meaningful relationships over many shallow ones.""",
        media=[]
    )
    
    print(f"\n✅ Profile Created!")
    print(f"   User ID: {result['user_id']}")
    print(f"   Action: {result['action'] or 'extract'}")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Operations: {result['operations']}")
    print(f"   File: {result['profile_path']}")
    
    # Show key extracted data
    profile = result['profile']
    print(f"\n📋 Extracted Information:")
    print(f"   Name: {profile.get('name')}")
    print(f"   Age: {profile.get('age')}")
    print(f"   Occupation: {profile.get('career', {}).get('current_occupation')}")
    print(f"   MBTI: {profile.get('personality', {}).get('mbti_type')}")
    print(f"   Hobbies: {', '.join(profile.get('interests', {}).get('hobbies', []))}")
    
    return user_id


def test_profile_refinement(user_id):
    """Test refining an existing profile with new information"""
    print("\n" + "="*60)
    print("TEST 2: Profile Refinement")
    print("="*60)
    
    result = process_input(
        user_id=user_id,
        message="""I forgot to mention - I also completed a DISC assessment and scored 
        high on D (Dominance) and I (Influence). I'm currently living in San Francisco, 
        and I speak English and Spanish fluently. My email is sarah.j@example.com.
        I practice yoga 3 times a week and follow a vegetarian diet.""",
        media=[]
    )
    
    print(f"\n✅ Profile Refined!")
    print(f"   Action: {result['action']}")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Operations: {result['operations']}")
    
    profile = result['profile']
    print(f"\n📋 Updated Information:")
    print(f"   Location: {profile.get('location')}")
    print(f"   Email: {profile.get('contact', {}).get('email')}")
    print(f"   DISC: {profile.get('personality', {}).get('disc_profile')}")
    print(f"   Languages: {', '.join(profile.get('communication', {}).get('language_preferences', []))}")
    print(f"   Exercise: {', '.join(profile.get('health', {}).get('exercise_routine', []))}")


def test_psychology_integration(user_id):
    """Test integrating psychology test results"""
    print("\n" + "="*60)
    print("TEST 3: Psychology Test Integration")
    print("="*60)
    
    result = process_input(
        user_id=user_id,
        message="""I just completed a Big Five personality test. My results were:
        - Openness: 85/100 (very high)
        - Conscientiousness: 75/100 (high)
        - Extraversion: 40/100 (moderately low)
        - Agreeableness: 65/100 (moderate)
        - Neuroticism: 35/100 (low)
        
        I also discovered my Enneagram type is Type 5 - The Investigator.
        My strengths include analytical thinking, problem-solving, and independence.
        Areas for improvement: social skills, emotional expression, and work-life balance.""",
        media=[]
    )
    
    print(f"\n✅ Psychology Profile Enhanced!")
    print(f"   Action: {result['action']}")
    print(f"   Confidence: {result['confidence']}")
    
    profile = result['profile']
    personality = profile.get('personality', {})
    
    print(f"\n🧠 Psychology Profile:")
    print(f"   MBTI: {personality.get('mbti_type')}")
    print(f"   DISC: {personality.get('disc_profile')}")
    print(f"   Enneagram: {personality.get('enneagram_type')}")
    
    big_five = personality.get('big_five', {})
    if big_five:
        print(f"   Big Five:")
        for trait, score in big_five.items():
            print(f"      - {trait.capitalize()}: {score}")
    
    strengths = personality.get('strengths', [])
    if strengths:
        print(f"   Strengths: {', '.join(strengths)}")


def test_goals_and_aspirations(user_id):
    """Test adding detailed goals and aspirations"""
    print("\n" + "="*60)
    print("TEST 4: Goals & Aspirations")
    print("="*60)
    
    result = process_input(
        user_id=user_id,
        message="""Let me share my goals in more detail:
        
        Short-term (next 6 months):
        - Complete a deep learning specialization
        - Contribute to an open-source AI project
        - Improve public speaking skills
        
        Long-term (next 3-5 years):
        - Become a senior ML engineer
        - Launch my own AI consulting business
        - Write a technical blog reaching 10k readers
        
        My core values are: continuous learning, authenticity, innovation, and helping others.
        My life purpose is to make advanced AI technology accessible to everyone.""",
        media=[]
    )
    
    print(f"\n✅ Goals Added!")
    print(f"   Action: {result['action']}")
    
    profile = result['profile']
    goals = profile.get('goals', {})
    
    print(f"\n🎯 Goals & Aspirations:")
    print(f"   Short-term goals: {len(goals.get('short_term_goals', []))}")
    for goal in goals.get('short_term_goals', [])[:3]:
        print(f"      • {goal}")
    
    print(f"   Long-term goals: {len(goals.get('long_term_goals', []))}")
    for goal in goals.get('long_term_goals', [])[:3]:
        print(f"      • {goal}")
    
    print(f"   Life purpose: {goals.get('life_purpose')}")
    print(f"   Core values: {', '.join(goals.get('values', []))}")


def test_profile_statistics(user_id):
    """Test getting comprehensive profile statistics"""
    print("\n" + "="*60)
    print("TEST 5: Profile Statistics")
    print("="*60)
    
    stats = get_profile_stats(user_id)
    
    if stats:
        print(f"\n📊 Profile Statistics for {stats['name']}:")
        print(f"   Overall Completeness: {stats['overall_completeness']}%")
        print(f"   Confidence Score: {stats['confidence']}")
        print(f"   Last Updated: {stats['last_updated']}")
        
        print(f"\n   Category Breakdown:")
        print(f"      Core Identity: {stats['core_identity_filled']}")
        print(f"      Contact Info: {stats['contact_filled']}")
        print(f"      Personality: {stats['personality_filled']}")
        print(f"      Goals: {stats['goals_filled']}")
        print(f"      Interests: {stats['interests_filled']}")
        
        print(f"\n   Content Counts:")
        print(f"      Hobbies: {stats['total_hobbies']}")
        print(f"      Interests: {stats['total_interests']}")
        print(f"      Short-term Goals: {stats['total_short_term_goals']}")
        print(f"      Long-term Goals: {stats['total_long_term_goals']}")
        print(f"      Skills: {stats['total_skills']}")
        print(f"      Test Results: {stats['total_test_results']}")
        
        print(f"\n   Psychology Profile:")
        print(f"      Has MBTI: {'✓' if stats['has_mbti'] else '✗'}")
        print(f"      Has DISC: {'✓' if stats['has_disc'] else '✗'}")
        print(f"      Has Enneagram: {'✓' if stats['has_enneagram'] else '✗'}")
        print(f"      Has Big Five: {'✓' if stats['has_big_five'] else '✗'}")
        
        print(f"\n   Data Quality:")
        print(f"      Sources: {', '.join(stats['extracted_sources'])}")
        print(f"      Is Complete: {'Yes' if stats['is_complete'] else 'No'}")
        print(f"      Needs Update: {'Yes' if stats['needs_update'] else 'No'}")


def test_profile_retrieval(user_id):
    """Test retrieving and displaying profile"""
    print("\n" + "="*60)
    print("TEST 6: Profile Retrieval")
    print("="*60)
    
    profile = get_profile(user_id)
    
    if profile:
        print(f"\n📄 Complete Profile for {profile.name}:")
        print(f"\n{json.dumps(profile.model_dump(), indent=2, default=str)[:1000]}...")
        print(f"\n   (Profile truncated for display)")
        
        # Show file size
        profile_path = f"database/user_profiles/{user_id}_profile.json"
        if os.path.exists(profile_path):
            file_size = os.path.getsize(profile_path)
            print(f"\n   Profile File Size: {file_size:,} bytes")


def test_multimodal_simulation(user_id):
    """Simulate multimodal input (without actual files)"""
    print("\n" + "="*60)
    print("TEST 7: Multimodal Input Simulation")
    print("="*60)
    
    print("\n   Note: This would normally include actual image/audio files")
    print("   Simulating with descriptive text instead...")
    
    result = process_input(
        user_id=user_id,
        message="""[Simulated voice input]: Hi, I'm recording this message to share more about myself.
        I have a moderate-pitched voice with a West Coast American accent. I tend to speak 
        at a moderate pace and my tone is usually warm and friendly.
        
        [Simulated photo analysis]: The photo shows a person with brown hair, hazel eyes,
        approximately 5'6" tall, with an athletic build. Distinguishing features include 
        a small scar on the left eyebrow and a passion for outdoor activities evident from 
        the hiking gear.""",
        media=[]
    )
    
    print(f"\n✅ Multimodal Data Processed!")
    print(f"   Action: {result['action']}")
    print(f"   Sources: {', '.join(result['profile'].get('extracted_from', []))}")
    
    profile = result['profile']
    print(f"\n   Voice Profile:")
    voice = profile.get('voice_profile', {})
    print(f"      Accent: {voice.get('accent')}")
    print(f"      Pitch: {voice.get('pitch')}")
    print(f"      Pace: {voice.get('pace')}")
    print(f"      Tone: {voice.get('tone')}")
    
    print(f"\n   Physical Attributes:")
    physical = profile.get('physical_attributes', {})
    print(f"      Hair: {physical.get('hair_color')}")
    print(f"      Eyes: {physical.get('eye_color')}")
    print(f"      Height: {physical.get('height')}")
    print(f"      Build: {physical.get('build')}")


def run_all_tests():
    """Run all profile schema tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  COMPREHENSIVE PROFILE EXTRACTOR SCHEMA TEST SUITE  ║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Run tests in sequence
        user_id = test_basic_profile_creation()
        test_profile_refinement(user_id)
        test_psychology_integration(user_id)
        test_goals_and_aspirations(user_id)
        test_profile_statistics(user_id)
        test_profile_retrieval(user_id)
        test_multimodal_simulation(user_id)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        # Final summary
        stats = get_profile_stats(user_id)
        print(f"\n📊 Final Profile Summary:")
        print(f"   User: {stats['name']}")
        print(f"   Completeness: {stats['overall_completeness']}%")
        print(f"   Confidence: {stats['confidence']}")
        print(f"   Test Results: {stats['total_test_results']}")
        print(f"   File: {stats['file_path']}")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
