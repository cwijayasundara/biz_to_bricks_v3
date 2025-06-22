#!/bin/bash

# Deploy Document Processing Server to Google Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [OPTIONS]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_SERVICE_NAME="document-processing-service"
DEFAULT_REPOSITORY_NAME="document-processing"
USE_SECRETS=false

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [PROJECT_ID] [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  PROJECT_ID              Google Cloud Project ID (optional, will prompt if not provided)"
    echo ""
    echo "Options:"
    echo "  -r, --region REGION     GCP region (default: $DEFAULT_REGION)"
    echo "  -s, --service SERVICE   Cloud Run service name (default: $DEFAULT_SERVICE_NAME)"
    echo "  -n, --repo REPO         Artifact Registry repository name (default: $DEFAULT_REPOSITORY_NAME)"
    echo "  --use-secrets           Use Secret Manager instead of environment variables"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 my-project-123"
    echo "  $0 my-project-123 --region us-west1"
    echo "  $0 my-project-123 --use-secrets"
    echo "  $0 --help"
}

# Check if Python is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
}

# Check if deploy script exists
check_deploy_script() {
    if [[ ! -f "deploy_to_cloudrun.py" ]]; then
        print_error "deploy_to_cloudrun.py not found in current directory"
        print_info "Please run this script from the server directory"
        exit 1
    fi
}

# Validate project ID format
validate_project_id() {
    local project_id="$1"
    if [[ ! "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
        print_error "Invalid project ID format" >&2
        print_info "Project ID must:" >&2
        print_info "- Start with a lowercase letter" >&2
        print_info "- Be 6-30 characters long" >&2
        print_info "- Contain only lowercase letters, numbers, and hyphens" >&2
        print_info "- End with a letter or number" >&2
        return 1
    fi
    return 0
}

# Prompt for project ID if not provided
get_project_id() {
    local project_id="$1"
    
    if [[ -z "$project_id" ]]; then
        echo "" >&2
        print_info "No project ID provided. Please enter your Google Cloud Project ID:" >&2
        read -p "Project ID: " project_id
        
        if [[ -z "$project_id" ]]; then
            print_error "Project ID cannot be empty" >&2
            exit 1
        fi
    fi
    
    if ! validate_project_id "$project_id"; then
        exit 1
    fi
    
    echo "$project_id"
}

# Main deployment function
deploy() {
    local project_id="$1"
    local region="$2"
    local service_name="$3"
    local repository_name="$4"
    local use_secrets="$5"
    
    print_info "Starting deployment with the following configuration:"
    echo "  Project ID: $project_id"
    echo "  Region: $region"
    echo "  Service Name: $service_name"
    echo "  Repository: $repository_name"
    echo "  Use Secrets: $use_secrets"
    echo ""
    
    # Confirm before proceeding
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
    
    print_info "Building deployment command..."
    
    # Build the command
    local cmd="python3 deploy_to_cloudrun.py --project-id \"$project_id\" --region \"$region\" --service-name \"$service_name\" --repository-name \"$repository_name\""
    
    if [[ "$use_secrets" == "true" ]]; then
        cmd="$cmd --use-secrets"
    fi
    
    print_info "Executing: $cmd"
    echo ""
    
    # Execute the deployment
    eval "$cmd"
    
    if [[ $? -eq 0 ]]; then
        print_success "Deployment completed successfully!"
    else
        print_error "Deployment failed"
        exit 1
    fi
}

# Parse command line arguments
PROJECT_ID=""
REGION="$DEFAULT_REGION"
SERVICE_NAME="$DEFAULT_SERVICE_NAME"
REPOSITORY_NAME="$DEFAULT_REPOSITORY_NAME"

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -n|--repo)
            REPOSITORY_NAME="$2"
            shift 2
            ;;
        --use-secrets)
            USE_SECRETS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$PROJECT_ID" ]]; then
                PROJECT_ID="$1"
            else
                print_error "Unexpected argument: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Main execution
main() {
    print_info "Document Processing Server - Cloud Run Deployment Script"
    echo "========================================================="
    echo ""
    
    # Check prerequisites
    check_python
    check_deploy_script
    
    # Get project ID
    PROJECT_ID=$(get_project_id "$PROJECT_ID")
    
    # Start deployment
    deploy "$PROJECT_ID" "$REGION" "$SERVICE_NAME" "$REPOSITORY_NAME" "$USE_SECRETS"
}

# Run main function
main "$@" 