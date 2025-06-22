#!/usr/bin/env python3
"""
Automated deployment script for Document Processing Server to Google Cloud Run.

This script automates the entire deployment process including:
- Prerequisites checking
- API enablement
- Artifact Registry repository creation
- Docker image building and pushing
- Cloud Run service deployment

Usage:
    python deploy_to_cloudrun.py --project-id your-project-id --region us-central1

Prerequisites:
- gcloud CLI installed and authenticated
- Docker installed
- .env file with required API keys in the server directory
- requirements.txt file in the server directory (included)
"""

import argparse
import os
import subprocess
import sys
import json
import time
from pathlib import Path


class CloudRunDeployer:
    def __init__(self, project_id: str, region: str = "us-central1", 
                 service_name: str = "document-processing-service",
                 repository_name: str = "document-processing"):
        self.project_id = project_id
        self.region = region
        self.service_name = service_name
        self.repository_name = repository_name
        self.image_name = "document-processing-server"
        self.image_tag = f"{region}-docker.pkg.dev/{project_id}/{repository_name}/{self.image_name}:latest"
        
    def run_command(self, command: list, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and handle errors."""
        print(f"Running: {' '.join(command)}")
        try:
            result = subprocess.run(
                command, 
                check=check, 
                capture_output=capture_output, 
                text=True
            )
            if result.stdout and capture_output:
                print(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {e}")
            if e.stderr:
                print(f"Error output: {e.stderr}")
            if check:
                sys.exit(1)
            return e
    
    def check_prerequisites(self):
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        # Check if gcloud is installed
        try:
            result = self.run_command(["gcloud", "version"])
            print("✅ gcloud CLI is installed")
        except FileNotFoundError:
            print("❌ gcloud CLI is not installed. Please install it first.")
            sys.exit(1)
        
        # Check if Docker is installed
        try:
            self.run_command(["docker", "--version"])
            print("✅ Docker is installed")
        except FileNotFoundError:
            print("❌ Docker is not installed. Please install it first.")
            sys.exit(1)
        
        # Check if authenticated
        try:
            result = self.run_command(["gcloud", "auth", "list", "--filter=status:ACTIVE"])
            if "ACTIVE" not in result.stdout:
                print("❌ Not authenticated with gcloud. Please run 'gcloud auth login'")
                sys.exit(1)
            print("✅ gcloud authentication verified")
        except Exception:
            print("❌ Error checking gcloud authentication")
            sys.exit(1)
        
        # Check if .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            print("❌ .env file not found. Please create it with your API keys.")
            sys.exit(1)
        print("✅ .env file found")
        
        # Validate .env file has required keys
        required_keys = ["OPENAI_API_KEY", "LLAMA_CLOUD_API_KEY", "PINECONE_API_KEY", "PINECONE_ENVIRONMENT"]
        env_content = env_file.read_text()
        missing_keys = [key for key in required_keys if key not in env_content]
        if missing_keys:
            print(f"❌ .env file is missing required keys: {missing_keys}")
            sys.exit(1)
        print("✅ .env file has all required keys")
    
    def load_env_vars(self) -> dict:
        """Load environment variables from .env file."""
        env_vars = {}
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value
        return env_vars
    
    def set_project(self):
        """Set the GCP project."""
        print(f"🔧 Setting GCP project to {self.project_id}...")
        self.run_command(["gcloud", "config", "set", "project", self.project_id])
        print("✅ Project set successfully")
    
    def enable_apis(self):
        """Enable required Google Cloud APIs."""
        print("🔧 Enabling required APIs...")
        apis = [
            "artifactregistry.googleapis.com",
            "run.googleapis.com",
            "cloudbuild.googleapis.com",
            "storage.googleapis.com"
        ]
        
        for api in apis:
            print(f"Enabling {api}...")
            self.run_command(["gcloud", "services", "enable", api])
        
        print("✅ All APIs enabled successfully")
        print("⏳ Waiting for APIs to propagate...")
        time.sleep(10)  # Give APIs time to propagate
    
    def configure_docker_auth(self):
        """Configure Docker authentication for Artifact Registry."""
        print("🔧 Configuring Docker authentication...")
        self.run_command([
            "gcloud", "auth", "configure-docker", 
            f"{self.region}-docker.pkg.dev", "--quiet"
        ])
        print("✅ Docker authentication configured")
    
    def create_artifact_registry(self):
        """Create Artifact Registry repository if it doesn't exist."""
        print(f"🔧 Creating Artifact Registry repository '{self.repository_name}'...")
        
        # Check if repository already exists
        try:
            result = self.run_command([
                "gcloud", "artifacts", "repositories", "describe", 
                self.repository_name, "--location", self.region
            ])
            print("✅ Artifact Registry repository already exists")
            return
        except subprocess.CalledProcessError:
            # Repository doesn't exist, create it
            pass
        
        self.run_command([
            "gcloud", "artifacts", "repositories", "create", self.repository_name,
            "--repository-format=docker",
            f"--location={self.region}",
            "--description=Docker repository for document processing service"
        ])
        print("✅ Artifact Registry repository created successfully")
    
    def create_storage_buckets(self):
        """Create Cloud Storage buckets for persistent file storage."""
        print("🔧 Creating Cloud Storage buckets...")
        
        bucket_names = [
            f"{self.project_id}-uploaded-files",
            f"{self.project_id}-parsed-files",
            f"{self.project_id}-summarized-files",
            f"{self.project_id}-bm25-indexes",
            f"{self.project_id}-generated-questions"
        ]
        
        for bucket_name in bucket_names:
            try:
                # Check if bucket exists
                result = self.run_command([
                    "gsutil", "ls", f"gs://{bucket_name}"
                ], check=False)
                
                if result.returncode == 0:
                    print(f"✅ Bucket {bucket_name} already exists")
                else:
                    # Create bucket
                    self.run_command([
                        "gsutil", "mb", "-l", self.region, f"gs://{bucket_name}"
                    ])
                    print(f"✅ Bucket {bucket_name} created successfully")
                    
            except Exception as e:
                print(f"⚠️ Could not create bucket {bucket_name}: {e}")
    
    def build_and_push_image(self):
        """Build and push Docker image to Artifact Registry."""
        print("🔧 Building Docker image...")
        
        # Build image for linux/amd64 platform
        self.run_command([
            "docker", "build", 
            "--platform", "linux/amd64",
            "-t", self.image_tag,
            "."
        ])
        print("✅ Docker image built successfully")
        
        print("🔧 Pushing image to Artifact Registry...")
        self.run_command(["docker", "push", self.image_tag])
        print("✅ Image pushed successfully")
    
    def deploy_to_cloudrun(self, env_vars: dict, use_secrets: bool = False):
        """Deploy the service to Cloud Run."""
        print("🚀 Deploying to Cloud Run...")
        
        deploy_cmd = [
            "gcloud", "run", "deploy", self.service_name,
            "--image", self.image_tag,
            "--region", self.region,
            "--platform", "managed",
            "--allow-unauthenticated",
            "--port", "8004",
            "--memory", "2Gi",
            "--cpu", "1"
        ]
        
        # Add project ID environment variable for Cloud Storage
        env_vars["GOOGLE_CLOUD_PROJECT"] = self.project_id
        
        if use_secrets:
            # Use Secret Manager (advanced option)
            secrets = [
                "OPENAI_API_KEY=openai-api-key:latest",
                "LLAMA_CLOUD_API_KEY=llama-cloud-api-key:latest", 
                "PINECONE_API_KEY=pinecone-api-key:latest",
                "PINECONE_ENVIRONMENT=pinecone-environment:latest"
            ]
            deploy_cmd.extend(["--set-secrets", ",".join(secrets)])
        else:
            # Use environment variables directly
            env_string = ",".join([f"{k}={v}" for k, v in env_vars.items()])
            deploy_cmd.extend(["--set-env-vars", env_string])
        
        self.run_command(deploy_cmd)
        print("✅ Service deployed successfully")
    
    def get_service_url(self) -> str:
        """Get the deployed service URL."""
        print("🔍 Getting service URL...")
        result = self.run_command([
            "gcloud", "run", "services", "describe", self.service_name,
            "--region", self.region,
            "--format=value(status.url)"
        ])
        
        url = result.stdout.strip()
        print(f"🌐 Service URL: {url}")
        return url
    
    def test_deployment(self, service_url: str):
        """Test the deployed service."""
        print("🧪 Testing deployment...")
        
        try:
            import requests
            
            # Test docs endpoint
            docs_url = f"{service_url}/docs"
            response = requests.get(docs_url, timeout=30)
            
            if response.status_code == 200:
                print("✅ Service is responding correctly")
                print(f"📖 API Documentation: {docs_url}")
            else:
                print(f"⚠️ Service responded with status code: {response.status_code}")
                
        except ImportError:
            print("📝 requests library not available for testing (install with: pip install requests)")
            print(f"📖 Please test manually at: {service_url}/docs")
        except Exception as e:
            print(f"⚠️ Error testing deployment: {e}")
            print(f"📖 Please test manually at: {service_url}/docs")
    
    def create_secrets(self, env_vars: dict):
        """Create secrets in Secret Manager (optional)."""
        print("🔐 Creating secrets in Secret Manager...")
        
        secret_mappings = {
            "OPENAI_API_KEY": "openai-api-key",
            "LLAMA_CLOUD_API_KEY": "llama-cloud-api-key",
            "PINECONE_API_KEY": "pinecone-api-key",
            "PINECONE_ENVIRONMENT": "pinecone-environment"
        }
        
        for env_key, secret_name in secret_mappings.items():
            if env_key in env_vars:
                try:
                    # Create secret
                    process = subprocess.Popen(
                        ["gcloud", "secrets", "create", secret_name],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    process.communicate(input=env_vars[env_key])
                    
                    print(f"✅ Secret {secret_name} created")
                except Exception as e:
                    print(f"⚠️ Could not create secret {secret_name}: {e}")
    
    def deploy(self, use_secrets: bool = False):
        """Run the complete deployment process."""
        print("🚀 Starting Cloud Run deployment process...")
        print(f"Project: {self.project_id}")
        print(f"Region: {self.region}")
        print(f"Service: {self.service_name}")
        print("=" * 50)
        
        try:
            # Step 1: Check prerequisites
            self.check_prerequisites()
            
            # Step 2: Load environment variables
            env_vars = self.load_env_vars()
            
            # Step 3: Set project
            self.set_project()
            
            # Step 4: Enable APIs
            self.enable_apis()
            
            # Step 5: Configure Docker auth
            self.configure_docker_auth()
            
            # Step 6: Create Artifact Registry
            self.create_artifact_registry()
            
            # Step 7: Create Cloud Storage buckets
            self.create_storage_buckets()
            
            # Step 8: Build and push image
            self.build_and_push_image()
            
            # Step 9: Create secrets (if requested)
            if use_secrets:
                self.create_secrets(env_vars)
            
            # Step 10: Deploy to Cloud Run
            self.deploy_to_cloudrun(env_vars, use_secrets)
            
            # Step 11: Get service URL
            service_url = self.get_service_url()
            
            # Step 12: Test deployment
            self.test_deployment(service_url)
            
            print("\n" + "=" * 50)
            print("🎉 Deployment completed successfully!")
            print(f"🌐 Service URL: {service_url}")
            print(f"📖 API Docs: {service_url}/docs")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Document Processing Server to Google Cloud Run"
    )
    parser.add_argument(
        "--project-id", 
        required=True, 
        help="Google Cloud Project ID"
    )
    parser.add_argument(
        "--region", 
        default="us-central1", 
        help="Google Cloud region (default: us-central1)"
    )
    parser.add_argument(
        "--service-name", 
        default="document-processing-service",
        help="Cloud Run service name (default: document-processing-service)"
    )
    parser.add_argument(
        "--repository-name", 
        default="document-processing",
        help="Artifact Registry repository name (default: document-processing)"
    )
    parser.add_argument(
        "--use-secrets",
        action="store_true",
        help="Use Secret Manager instead of environment variables"
    )
    
    args = parser.parse_args()
    
    deployer = CloudRunDeployer(
        project_id=args.project_id,
        region=args.region,
        service_name=args.service_name,
        repository_name=args.repository_name
    )
    
    deployer.deploy(use_secrets=args.use_secrets)


if __name__ == "__main__":
    main() 