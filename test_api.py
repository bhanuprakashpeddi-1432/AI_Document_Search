#!/usr/bin/env python3
"""
Test script for HackRX solution
Run this script to validate the API functionality
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
API_TOKEN = "hackrx-default-token"  # Update with your token
TEST_DOCUMENT_URL = "https://hackrx.blob.core.windows.net/assets/policy.pdf"
TEST_QUESTIONS = [
    "What is the grace period for premium payment?",
    "What is the waiting period for cataract surgery?",
    "What are the eligibility criteria for the policy?"
]

def test_health_endpoint():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {str(e)}")
        return False

def test_main_endpoint():
    """Test the main /hackrx/run endpoint"""
    print("🧪 Testing main endpoint...")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "documents": TEST_DOCUMENT_URL,
        "questions": TEST_QUESTIONS
    }
    
    try:
        print("📤 Sending request...")
        start_time = time.time()
        
        response = requests.post(
            f"{API_BASE_URL}/hackrx/run",
            headers=headers,
            json=payload,
            timeout=120  # 2 minute timeout
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Main endpoint working (took {processing_time:.2f}s)")
            print(f"📊 Received {len(result.get('answers', []))} answers")
            
            # Display results
            for i, answer in enumerate(result.get('answers', []), 1):
                print(f"\n📝 Question {i}: {TEST_QUESTIONS[i-1]}")
                print(f"💡 Answer: {answer[:200]}...")
                
                sources = result.get('sources', [[]])[i-1] if result.get('sources') else []
                print(f"📚 Sources: {len(sources)} chunks")
            
            return True
        else:
            print(f"❌ Main endpoint failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Main endpoint error: {str(e)}")
        return False

def test_authentication():
    """Test authentication"""
    print("🔐 Testing authentication...")
    
    # Test without token
    try:
        response = requests.post(f"{API_BASE_URL}/hackrx/run", json={})
        if response.status_code == 401:
            print("✅ Authentication working (unauthorized access blocked)")
            return True
        else:
            print(f"❌ Authentication issue: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Authentication test error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 HackRX API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Authentication", test_authentication),
        ("Main Endpoint", test_main_endpoint)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔧 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Your HackRX solution is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the logs and configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
