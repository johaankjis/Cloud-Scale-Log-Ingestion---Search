"""
Test script for Query API
"""
import requests
from datetime import datetime, timedelta
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.json()}")
    assert response.status_code == 200


def test_query_logs():
    """Test log query"""
    query = {
        "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "limit": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/logs", json=query)
    print(f"\nQuery logs response:")
    print(json.dumps(response.json(), indent=2, default=str))
    assert response.status_code == 200


def test_aggregate():
    """Test aggregation"""
    params = {
        "start_time": (datetime.now() - timedelta(hours=24)).isoformat()
    }
    
    response = requests.get(f"{BASE_URL}/api/v1/logs/aggregate", params=params)
    print(f"\nAggregation response:")
    print(json.dumps(response.json(), indent=2, default=str))
    assert response.status_code == 200


def test_errors():
    """Test error logs"""
    response = requests.get(f"{BASE_URL}/api/v1/logs/errors")
    print(f"\nError logs response:")
    print(json.dumps(response.json(), indent=2, default=str))
    assert response.status_code == 200


if __name__ == '__main__':
    print("Testing Query API...")
    test_health()
    test_query_logs()
    test_aggregate()
    test_errors()
    print("\nAll tests passed!")
