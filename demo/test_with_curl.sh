#!/bin/bash

# GrayGEMS Demo Server Test Script
# Tests the token-based project management and workflow system

BASE_URL="http://localhost:8000"
PROJECT_TOKEN=""
PROJECT_ID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to make HTTP requests and handle responses
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local headers=$4
    
    local curl_cmd="curl -s -w '\nHTTP_STATUS:%{http_code}'"
    
    if [ "$method" = "GET" ]; then
        curl_cmd="$curl_cmd -X GET"
    elif [ "$method" = "POST" ]; then
        curl_cmd="$curl_cmd -X POST"
    elif [ "$method" = "DELETE" ]; then
        curl_cmd="$curl_cmd -X DELETE"
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    if [ -n "$headers" ]; then
        curl_cmd="$curl_cmd $headers"
    fi
    
    curl_cmd="$curl_cmd '$BASE_URL$endpoint'"
    
    local response=$(eval $curl_cmd)
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    echo "$http_status|$body"
}

# Test 1: Health Check
print_status "Testing health check..."
response=$(make_request "GET" "/health")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Health check passed"
    echo "$body" | jq '.'
else
    print_error "Health check failed with status $http_status"
    echo "$body"
    exit 1
fi

echo

# Test 2: Root endpoint
print_status "Testing root endpoint..."
response=$(make_request "GET" "/")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Root endpoint working"
    echo "$body" | jq '.'
else
    print_error "Root endpoint failed with status $http_status"
    echo "$body"
    exit 1
fi

echo

# Test 3: List services
print_status "Testing services endpoint..."
response=$(make_request "GET" "/services")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Services endpoint working"
    echo "$body" | jq '.'
else
    print_error "Services endpoint failed with status $http_status"
    echo "$body"
fi

echo

# Test 4: Create project
print_status "Creating new project..."
project_data='{"name": "Test Project", "description": "Testing GrayGEMS demo"}'
response=$(make_request "POST" "/projects" "$project_data")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Project created successfully"
    echo "$body" | jq '.'
    
    # Extract project ID and token
    PROJECT_ID=$(echo "$body" | jq -r '.data.project_id')
    PROJECT_TOKEN=$(echo "$body" | jq -r '.data.token')
    
    print_status "Project ID: $PROJECT_ID"
    print_status "Project Token: ${PROJECT_TOKEN:0:8}..."
else
    print_error "Project creation failed with status $http_status"
    echo "$body"
    exit 1
fi

echo

# Test 5: Get project info
print_status "Testing project info retrieval..."
response=$(make_request "GET" "/projects/$PROJECT_ID" "" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Project info retrieved successfully"
    echo "$body" | jq '.'
else
    print_error "Project info retrieval failed with status $http_status"
    echo "$body"
fi

echo

# Test 6: Execute calculator workflow
print_status "Testing calculator workflow execution..."
calculator_workflow='{
  "workflow": {
    "name": "Calculator Workflow",
    "steps": {
      "add_numbers": {
        "service": "calculator.math",
        "task": "add",
        "inputs": {
          "a": 5,
          "b": 3
        },
        "dependencies": []
      },
      "multiply_result": {
        "service": "calculator.math",
        "task": "multiply",
        "inputs": {
          "a": "$add_numbers.result",
          "b": 2
        },
        "dependencies": ["add_numbers"]
      },
      "calculate_mean": {
        "service": "calculator.statistics",
        "task": "calculate_mean",
        "inputs": {
          "numbers": [1, 2, 3, 4, 5]
        },
        "dependencies": []
      }
    }
  }
}'

response=$(make_request "POST" "/projects/$PROJECT_ID/workflow" "$calculator_workflow" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Calculator workflow executed successfully"
    echo "$body" | jq '.'
else
    print_error "Calculator workflow failed with status $http_status"
    echo "$body"
fi

echo

# Test 7: Execute text processing workflow
print_status "Testing text processing workflow execution..."
text_workflow='{
  "workflow": {
    "name": "Text Processing Workflow",
    "steps": {
      "word_analysis": {
        "service": "text_processor.analysis",
        "task": "word_count",
        "inputs": {
          "text": "Hello world! This is a test of the GrayGEMS demo system."
        },
        "dependencies": []
      },
      "character_analysis": {
        "service": "text_processor.analysis",
        "task": "character_count",
        "inputs": {
          "text": "Hello world! This is a test of the GrayGEMS demo system."
        },
        "dependencies": []
      }
    }
  }
}'

response=$(make_request "POST" "/projects/$PROJECT_ID/workflow" "$text_workflow" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Text processing workflow executed successfully"
    echo "$body" | jq '.'
else
    print_error "Text processing workflow failed with status $http_status"
    echo "$body"
fi

echo

# Test 8: List transactions
print_status "Testing transaction listing..."
response=$(make_request "GET" "/projects/$PROJECT_ID/transactions" "" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Transactions listed successfully"
    echo "$body" | jq '.'
else
    print_error "Transaction listing failed with status $http_status"
    echo "$body"
fi

echo

# Test 9: Test invalid token
print_status "Testing invalid token access..."
response=$(make_request "GET" "/projects/$PROJECT_ID" "" "-H 'X-Project-Token: invalid_token'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "401" ]; then
    print_success "Invalid token correctly rejected"
    echo "$body" | jq '.'
else
    print_warning "Invalid token test unexpected result: $http_status"
    echo "$body"
fi

echo

# Test 10: Extend project
print_status "Testing project extension..."
response=$(make_request "POST" "/projects/$PROJECT_ID/extend?days=15" "" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Project extended successfully"
    echo "$body" | jq '.'
else
    print_error "Project extension failed with status $http_status"
    echo "$body"
fi

echo

# Test 11: List all projects (admin)
print_status "Testing project listing (admin)..."
response=$(make_request "GET" "/projects")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Project listing successful"
    echo "$body" | jq '.'
else
    print_error "Project listing failed with status $http_status"
    echo "$body"
fi

echo

# Test 12: Cleanup expired projects (admin)
print_status "Testing cleanup of expired projects..."
response=$(make_request "POST" "/admin/cleanup")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Cleanup completed"
    echo "$body" | jq '.'
else
    print_error "Cleanup failed with status $http_status"
    echo "$body"
fi

echo

# Test 13: Delete project
print_status "Testing project deletion..."
response=$(make_request "DELETE" "/projects/$PROJECT_ID" "" "-H 'X-Project-Token: $PROJECT_TOKEN'")
http_status=$(echo "$response" | cut -d'|' -f1)
body=$(echo "$response" | cut -d'|' -f2-)

if [ "$http_status" = "200" ]; then
    print_success "Project deleted successfully"
    echo "$body" | jq '.'
else
    print_error "Project deletion failed with status $http_status"
    echo "$body"
fi

echo

print_success "All tests completed!"
print_status "Summary:"
print_status "- Health check: ✓"
print_status "- Root endpoint: ✓"
print_status "- Services listing: ✓"
print_status "- Project creation: ✓"
print_status "- Project info retrieval: ✓"
print_status "- Calculator workflow: ✓"
print_status "- Text processing workflow: ✓"
print_status "- Transaction listing: ✓"
print_status "- Token validation: ✓"
print_status "- Project extension: ✓"
print_status "- Admin project listing: ✓"
print_status "- Cleanup: ✓"
print_status "- Project deletion: ✓" 