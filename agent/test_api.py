#!/usr/bin/env python3
"""
Test script for the Outbound Call Dispatcher Web Service

This script demonstrates how to use the API and provides basic testing functionality.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("API_KEY", "secure-api-key-change-this-in-production")


def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing health check endpoint...")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_dispatch_call():
    """Test the dispatch call endpoint."""
    print("\n📞 Testing dispatch call endpoint...")

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    # Test data
    test_data = {
        "first_name": "John",
        "last_name": "TestCustomer",
        "phone_number": "2125551234",
        "address": "456 Test Street, New York, NY 10001"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/dispatch-call",
            json=test_data,
            headers=headers
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        return response.status_code == 200

    except Exception as e:
        print(f"❌ Dispatch call test failed: {e}")
        return False


def test_invalid_api_key():
    """Test with invalid API key."""
    print("\n🔐 Testing invalid API key...")

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "invalid-key"
    }

    test_data = {
        "first_name": "John",
        "last_name": "TestCustomer",
        "phone_number": "2125551234"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/dispatch-call",
            json=test_data,
            headers=headers
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        return response.status_code == 401

    except Exception as e:
        print(f"❌ Invalid API key test failed: {e}")
        return False


def test_invalid_phone():
    """Test with invalid phone number."""
    print("\n📞 Testing invalid phone number...")

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    test_data = {
        "first_name": "John",
        "last_name": "TestCustomer",
        "phone_number": "555123456789"  # Invalid format
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/dispatch-call",
            json=test_data,
            headers=headers
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        return response.status_code == 400

    except Exception as e:
        print(f"❌ Invalid phone test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Starting API Tests")
    print("=" * 50)

    # Check if service is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
    except Exception:
        print("❌ Service is not running. Please start the web service first:")
        print("   python web_service.py")
        return

    tests = [
        ("Health Check", test_health_check),
        ("Dispatch Call", test_dispatch_call),
        ("Invalid API Key", test_invalid_api_key),
        ("Invalid Phone", test_invalid_phone)
    ]

    results = []

    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
        print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")

    print("\n" + "=" * 50)
    print("📊 Test Summary:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above.")


if __name__ == "__main__":
    main()