#!/usr/bin/env python3
"""
Test script for GrayGEMS Demo Server
Tests all endpoints and functionality, saves responses for client testing
"""

import requests
import json
import time
import os
from pathlib import Path
from datetime import datetime

# Server configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Test results directory
TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(exist_ok=True)

def save_response(test_name: str, response_data: dict, status_code: int = 200):
    """Save API response to file for client testing"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_{timestamp}.json"
    filepath = TEST_RESULTS_DIR / filename
    
    response_data["_metadata"] = {
        "test_name": test_name,
        "timestamp": timestamp,
        "status_code": status_code,
        "url": BASE_URL
    }
    
    with open(filepath, 'w') as f:
        json.dump(response_data, f, indent=2)
    
    print(f"💾 Saved response: {filepath}")
    return filepath

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
            save_response("health_check", data, response.status_code)
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            save_response("health_check_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        save_response("health_check_error", {"error": str(e)}, 500)
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
            save_response("root_endpoint", data, response.status_code)
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            save_response("root_endpoint_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        save_response("root_endpoint_error", {"error": str(e)}, 500)
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
            save_response("services_list", data, response.status_code)
            return True
        else:
            print(f"❌ Services endpoint failed: {response.status_code}")
            save_response("services_list_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Services endpoint error: {e}")
        save_response("services_list_error", {"error": str(e)}, 500)
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
            save_response("project_creation", data, response.status_code)
            return project_id, token
        else:
            print(f"❌ Project creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("project_creation_failed", {"error": response.text}, response.status_code)
            return None, None
    except Exception as e:
        print(f"❌ Project creation error: {e}")
        save_response("project_creation_error", {"error": str(e)}, 500)
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
            save_response("project_get", data, response.status_code)
            return True
        else:
            print(f"❌ Get project failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("project_get_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Get project error: {e}")
        save_response("project_get_error", {"error": str(e)}, 500)
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
            save_response("workflow_execution", data, response.status_code)
            return True
        else:
            print(f"❌ Workflow execution failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("workflow_execution_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Workflow execution error: {e}")
        save_response("workflow_execution_error", {"error": str(e)}, 500)
        return False

def test_download(project_id, token):
    """Test file download endpoint"""
    print(f"\n📥 Testing file download...")
    try:
        headers = {"X-Project-Token": token}
        # Test both files that were created by the workflows
        files_to_test = [
            "outputs/result.txt",  # Created by basic workflow
            "outputs/complex_results.txt"  # Created by complex workflow
        ]
        
        # Create downloads directory
        downloads_dir = Path(__file__).parent / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        for file_path in files_to_test:
            response = requests.get(f"{BASE_URL}/projects/{project_id}/download/{file_path}", 
                                  headers=headers)
            if response.status_code == 200:
                print(f"✅ File download successful: {file_path}")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {response.headers.get('content-length', 'unknown')} bytes")
                
                # Save the actual file content to downloads directory
                safe_filename = file_path.replace('/', '_')
                download_filename = f"file_download_{project_id}_{safe_filename}"
                download_path = downloads_dir / download_filename
                with open(download_path, 'wb') as f:
                    f.write(response.content)
                print(f"   Saved to: {download_path}")
                
                # Try to decode as text for display
                try:
                    content_text = response.content.decode('utf-8')
                    print(f"   Content preview: {content_text[:100]}...")
                except:
                    print(f"   Content: Binary file")
                
                save_response(f"file_download_{safe_filename}", {
                    "file_path": file_path,
                    "download_path": str(download_path),
                    "content_length": response.headers.get('content-length'),
                    "content_type": response.headers.get('content-type'),
                    "content_preview": response.content.decode('utf-8')[:200] if response.content else ""
                }, response.status_code)
            else:
                print(f"❌ File download failed for {file_path}: {response.status_code}")
                print(f"   Response: {response.text}")
                save_response(f"file_download_failed_{file_path.replace('/', '_')}", {"error": response.text}, response.status_code)
        
        return True
    except Exception as e:
        print(f"❌ File download error: {e}")
        save_response("file_download_error", {"error": str(e)}, 500)
        return False

def test_archive_download(project_id, token):
    """Test project archive download"""
    print(f"\n📦 Testing project archive download...")
    try:
        headers = {"X-Project-Token": token}
        
        # First, create the project archive
        print("   Creating project archive...")
        create_archive_response = requests.post(f"{BASE_URL}/projects/{project_id}/archive", 
                                              headers=headers)
        if create_archive_response.status_code != 200:
            print(f"❌ Failed to create archive: {create_archive_response.status_code}")
            print(f"   Response: {create_archive_response.text}")
            save_response("archive_creation_failed", {"error": create_archive_response.text}, create_archive_response.status_code)
            return False
        
        archive_data = create_archive_response.json()
        archive_filename = archive_data['data']['archive_filename']
        print(f"   Archive created: {archive_filename}")
        print(f"   Size: {archive_data['data']['archive_size']} bytes")
        
        # Now test downloading the archive using the correct filename
        response = requests.get(f"{BASE_URL}/projects/{project_id}/download/{archive_filename}", 
                              headers=headers)
        if response.status_code == 200:
            print(f"✅ Archive download successful")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"   Content-Length: {response.headers.get('content-length', 'unknown')} bytes")
            
            # Save the actual file content to downloads directory
            downloads_dir = Path(__file__).parent / "downloads"
            downloads_dir.mkdir(exist_ok=True)
            
            download_filename = f"archive_download_{project_id}.zip"
            download_path = downloads_dir / download_filename
            with open(download_path, 'wb') as f:
                f.write(response.content)
            print(f"   Saved to: {download_path}")
            
            save_response("archive_download", {
                "archive_filename": archive_filename,
                "download_path": str(download_path),
                "content_length": response.headers.get('content-length'),
                "content_type": response.headers.get('content-type')
            }, response.status_code)
            return True
        else:
            print(f"❌ Archive download failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("archive_download_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Archive download error: {e}")
        save_response("archive_download_error", {"error": str(e)}, 500)
        return False

def test_invalid_token(project_id):
    """Test invalid token access"""
    print(f"\n🚫 Testing invalid token access...")
    try:
        headers = {"X-Project-Token": "invalid_token_12345"}
        response = requests.get(f"{BASE_URL}/projects/{project_id}", headers=headers)
        if response.status_code == 401:
            data = response.json()
            print(f"✅ Invalid token correctly rejected")
            print(f"   Error: {data.get('error', 'Unknown error')}")
            save_response("invalid_token_test", data, response.status_code)
            return True
        else:
            print(f"⚠️ Invalid token test unexpected result: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("invalid_token_test_unexpected", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Invalid token test error: {e}")
        save_response("invalid_token_test_error", {"error": str(e)}, 500)
        return False

def test_project_extension(project_id, token):
    """Test project extension"""
    print(f"\n⏰ Testing project extension...")
    try:
        headers = {"X-Project-Token": token}
        response = requests.post(f"{BASE_URL}/projects/{project_id}/extend?days=15", 
                               headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Project extended successfully")
            print(f"   Message: {data.get('message', 'No message')}")
            save_response("project_extension", data, response.status_code)
            return True
        else:
            print(f"❌ Project extension failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("project_extension_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Project extension error: {e}")
        save_response("project_extension_error", {"error": str(e)}, 500)
        return False

def test_project_deletion(project_id, token):
    """Test project deletion"""
    print(f"\n🗑️ Testing project deletion...")
    try:
        headers = {"X-Project-Token": token}
        response = requests.delete(f"{BASE_URL}/projects/{project_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Project deleted successfully")
            print(f"   Message: {data.get('message', 'No message')}")
            save_response("project_deletion", data, response.status_code)
            return True
        else:
            print(f"❌ Project deletion failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("project_deletion_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Project deletion error: {e}")
        save_response("project_deletion_error", {"error": str(e)}, 500)
        return False

def test_complex_workflow(project_id, token):
    """Test a more complex workflow with multiple steps"""
    print(f"\n🔄 Testing complex workflow...")
    try:
        # Complex workflow with multiple calculator operations and file outputs
        workflow_data = {
            "workflow": {
                "name": "Complex Calculator Workflow",
                "steps": {
                    "add": {
                        "service": "calculator.math",
                        "task": "add",
                        "inputs": {
                            "a": 10,
                            "b": 20
                        },
                        "dependencies": []
                    },
                    "multiply": {
                        "service": "calculator.multiply",
                        "task": "multiply",
                        "inputs": {
                            "a": 5,
                            "b": 3
                        },
                        "dependencies": []
                    },
                    "calculate_mean": {
                        "service": "calculator.statistics",
                        "task": "calculate_mean",
                        "inputs": {
                            "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                        },
                        "dependencies": []
                    },
                    "save_results": {
                        "service": "file_utils",
                        "task": "process_file",
                        "inputs": {
                            "operation": "write",
                            "source_path": "outputs/complex_results.txt",
                            "content": "Complex Calculator Results:\nAddition: $add.result\nMultiplication: $multiply.result\nMean: $calculate_mean.result"
                        },
                        "dependencies": ["add", "multiply", "calculate_mean"]
                    }
                }
            }
        }
        
        headers = {"X-Project-Token": token}
        response = requests.post(f"{BASE_URL}/projects/{project_id}/workflow", 
                               json=workflow_data, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Complex workflow executed successfully")
            print(f"   Steps completed: {len(data['data']['steps'])}")
            save_response("complex_workflow", data, response.status_code)
            return True
        else:
            print(f"❌ Complex workflow failed: {response.status_code}")
            print(f"   Response: {response.text}")
            save_response("complex_workflow_failed", {"error": response.text}, response.status_code)
            return False
    except Exception as e:
        print(f"❌ Complex workflow error: {e}")
        save_response("complex_workflow_error", {"error": str(e)}, 500)
        return False

def main():
    """Run all tests"""
    print("🚀 Starting GrayGEMS Demo Tests")
    print("=" * 50)
    print(f"📁 Test results will be saved to: {TEST_RESULTS_DIR.absolute()}")
    print()
    
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
        print("❌ Basic workflow execution failed")
        return
    
    # Test complex workflow
    if not test_complex_workflow(project_id, token):
        print("❌ Complex workflow execution failed")
        return
    
    # Test file downloads
    if not test_download(project_id, token):
        print("❌ File download failed")
        return
    
    # Test archive download
    if not test_archive_download(project_id, token):
        print("❌ Archive download failed")
        return
    
    # Test security features
    if not test_invalid_token(project_id):
        print("❌ Invalid token test failed")
        return
    
    # Test project management
    if not test_project_extension(project_id, token):
        print("❌ Project extension failed")
        return
    
    # Test project deletion
    if not test_project_deletion(project_id, token):
        print("❌ Project deletion failed")
        return
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print(f"📁 Project ID: {project_id}")
    print(f"🔑 Token: {token[:8]}...")
    print(f"💾 Test results saved to: {TEST_RESULTS_DIR.absolute()}")
    
    # Create a summary file
    summary = {
        "test_summary": {
            "timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "token_prefix": token[:8] + "...",
            "tests_passed": [
                "health_check",
                "root_endpoint", 
                "services_list",
                "project_creation",
                "project_get",
                "workflow_execution",
                "complex_workflow",
                "file_download",
                "archive_download",
                "invalid_token_test",
                "project_extension",
                "project_deletion"
            ],
            "test_results_directory": str(TEST_RESULTS_DIR.absolute())
        }
    }
    
    summary_file = TEST_RESULTS_DIR / "test_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📋 Test summary saved to: {summary_file}")

if __name__ == "__main__":
    main() 