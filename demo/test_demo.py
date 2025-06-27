#!/usr/bin/env python3
"""
Test script for GrayGEMS Demo Server
Tests all endpoints and functionality
"""

import requests
import json
import time
from pathlib import Path

# Server configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['message']}")
            print(f"   Services: {data['data']['services']}")
            print(f"   Projects: {data['data']['projects']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n🏠 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data['message']}")
            print(f"   Version: {data['data']['version']}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_services():
    """Test services endpoint"""
    print("\n🔧 Testing services endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/services")
        if response.status_code == 200:
            data = response.json()
            services = data['data']['services']
            print(f"✅ Services endpoint: {len(services)} services found")
            for service_name, service_info in services.items():
                print(f"   {service_name}: {len(service_info['tasks'])} tasks")
            return True
        else:
            print(f"❌ Services endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Services endpoint error: {e}")
        return False

def test_create_project():
    """Test project creation"""
    print("\n📁 Testing project creation...")
    try:
        project_data = {
            "name": "Test Project",
            "description": "A test project for GrayGEMS demo"
        }
        
        response = requests.post(f"{BASE_URL}/projects", json=project_data, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            project_id = data['data']['project_id']
            token = data['data']['token']
            print(f"✅ Project created: {project_id}")
            print(f"   Token: {token[:8]}...")
            return project_id, token
        else:
            print(f"❌ Project creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Project creation error: {e}")
        return None, None

def test_get_project(project_id, token):
    """Test getting project details"""
    print(f"\n📋 Testing get project: {project_id}")
    try:
        headers = {"X-Project-Token": token}
        response = requests.get(f"{BASE_URL}/projects/{project_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Project retrieved: {data['data']['name']}")
            print(f"   Status: {data['data']['status']}")
            return True
        else:
            print(f"❌ Get project failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Get project error: {e}")
        return False

def test_workflow(project_id, token):
    """Test workflow execution"""
    print(f"\n⚙️ Testing workflow execution...")
    try:
        # Calculator workflow with file output
        workflow_data = {
            "workflow": {
                "name": "Calculator with File Output",
                "steps": {
                    "add": {
                        "service": "calculator.math",
                        "task": "add",
                        "inputs": {
                            "a": 5,
                            "b": 3
                        },
                        "dependencies": []
                    },
                    "save_result": {
                        "service": "file_utils",
                        "task": "process_file",
                        "inputs": {
                            "operation": "write",
                            "source_path": "outputs/result.txt",
                            "content": "Addition result: $add.result"
                        },
                        "dependencies": ["add"]
                    }
                }
            }
        }
        
        headers = {"X-Project-Token": token}
        response = requests.post(f"{BASE_URL}/projects/{project_id}/workflow", 
                               json=workflow_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Workflow executed successfully")
            print(f"   Result: {data['data']}")
            return True
        else:
            print(f"❌ Workflow execution failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Workflow execution error: {e}")
        return False

def test_download(project_id, token):
    """Test file download endpoint"""
    print(f"\n📥 Testing file download...")
    try:
        headers = {"X-Project-Token": token}
        response = requests.get(f"{BASE_URL}/projects/{project_id}/download/outputs/result.txt", 
                              headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File download info retrieved")
            print(f"   File: {data['data']['file_path']}")
            print(f"   Size: {data['data']['size']} bytes")
            return True
        else:
            print(f"❌ File download failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ File download error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting GrayGEMS Demo Tests")
    print("=" * 50)
    
    # Test basic endpoints
    if not test_health():
        print("❌ Health check failed, server may not be running")
        return
    
    if not test_root():
        print("❌ Root endpoint failed")
        return
    
    if not test_services():
        print("❌ Services endpoint failed")
        return
    
    # Test project functionality
    project_id, token = test_create_project()
    if not project_id or not token:
        print("❌ Project creation failed")
        return
    
    if not test_get_project(project_id, token):
        print("❌ Get project failed")
        return
    
    # Test workflow execution
    if not test_workflow(project_id, token):
        print("❌ Workflow execution failed")
        return
    
    # Test file download
    if not test_download(project_id, token):
        print("❌ File download failed")
        return
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print(f"📁 Project ID: {project_id}")
    print(f"🔑 Token: {token[:8]}...")

if __name__ == "__main__":
    main() 