#!/usr/bin/env python3
"""
Document Processing Server Startup Script

This script provides easy control over storage mode and other server settings.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start Document Processing Server with configurable storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with local storage (development)
  python start_server.py --storage local
  
  # Start with cloud storage (production)
  python start_server.py --storage cloud
  
  # Start with auto-detection (default)
  python start_server.py --storage auto
  
  # Start on custom host/port
  python start_server.py --host 0.0.0.0 --port 8005 --storage local
  
  # Start with reload for development
  python start_server.py --storage local --reload
        """
    )
    
    parser.add_argument(
        '--storage', 
        choices=['local', 'cloud', 'auto'],
        default='auto',
        help='Storage mode: local (filesystem), cloud (Cloud Storage), auto (detect)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind the server to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8004,
        help='Port to bind the server to (default: 8004)'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload for development'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['debug', 'info', 'warning', 'error'],
        default='info',
        help='Log level (default: info)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker processes (default: 1)'
    )
    
    return parser.parse_args()

def validate_environment(storage_mode):
    """Validate environment based on storage mode."""
    print(f"🔍 Validating environment for storage mode: {storage_mode}")
    
    if storage_mode == 'cloud':
        # Check for cloud storage requirements
        required_env_vars = ['GOOGLE_CLOUD_PROJECT']
        missing_vars = []
        
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables for cloud storage: {missing_vars}")
            print("   Please set GOOGLE_CLOUD_PROJECT environment variable")
            return False
        
        # Check if running in Cloud Run
        if os.getenv('K_SERVICE'):
            print("✅ Running in Cloud Run environment")
        else:
            print("⚠️  Running cloud storage locally - ensure you have proper authentication")
    
    elif storage_mode == 'local':
        print("✅ Using local filesystem storage")
        
        # Create local directories if they don't exist
        directories = ['uploaded_files', 'parsed_files', 'summarized_files', 'bm25_indexes']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
        print(f"✅ Local directories ensured: {directories}")
    
    else:  # auto
        print("✅ Auto-detection mode - will determine storage based on environment")
    
    return True

def set_environment_variables(args):
    """Set environment variables based on arguments."""
    # Set storage mode
    os.environ['STORAGE_MODE'] = args.storage
    
    # Set other environment variables if needed
    if args.log_level:
        os.environ['LOG_LEVEL'] = args.log_level.upper()

def check_port_available(port):
    """Check if the specified port is available."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return True  # Assume available if we can't check

def start_server(args):
    """Start the uvicorn server with the specified configuration."""
    
    # Check if port is available
    if not check_port_available(args.port):
        print(f"⚠️  Port {args.port} is already in use. Please use a different port or stop the existing service.")
        sys.exit(1)
    
    # Build uvicorn command
    cmd = [
        'uvicorn',
        'app:app',
        '--host', args.host,
        '--port', str(args.port),
        '--log-level', args.log_level
    ]
    
    if args.reload:
        cmd.append('--reload')
    
    if args.workers > 1 and not args.reload:
        cmd.extend(['--workers', str(args.workers)])
    elif args.workers > 1 and args.reload:
        print("⚠️  Cannot use multiple workers with reload. Using single worker.")
    
    # Display URLs with localhost for better user experience
    display_host = 'localhost' if args.host == '0.0.0.0' else args.host
    
    print(f"🚀 Starting server with command: {' '.join(cmd)}")
    print(f"📍 Server will be available at: http://{display_host}:{args.port}")
    print(f"📖 API documentation: http://{display_host}:{args.port}/docs")
    print(f"💾 Storage mode: {args.storage}")
    print("")
    
    try:
        # Check if uvicorn is available
        subprocess.run(['uvicorn', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ uvicorn is not installed or not available in PATH")
        print("   Please install uvicorn: pip install uvicorn")
        sys.exit(1)
    
    try:
        # Start the server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        print("   Check the error logs above for more details")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def validate_working_directory():
    """Validate that we're running from the correct directory."""
    current_dir = Path.cwd()
    app_file = current_dir / "app.py"
    
    if not app_file.exists():
        print("❌ app.py not found in current directory")
        print(f"   Current directory: {current_dir}")
        print("   Please run this script from the server directory containing app.py")
        return False
    
    print(f"✅ Running from correct directory: {current_dir}")
    return True

def main():
    """Main function."""
    print("🔧 Document Processing Server Startup")
    print("=" * 50)
    
    # Validate working directory
    if not validate_working_directory():
        sys.exit(1)
    
    # Parse arguments
    args = parse_arguments()
    
    # Validate environment
    if not validate_environment(args.storage):
        sys.exit(1)
    
    # Set environment variables
    set_environment_variables(args)
    
    # Start server
    start_server(args)

if __name__ == "__main__":
    main() 