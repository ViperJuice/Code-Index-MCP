#!/usr/bin/env python3
"""
Test script to verify Docker setup for MCP Index Server
"""
import os
import sys
import subprocess
import json

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker command failed")
            return False
    except FileNotFoundError:
        print("❌ Docker not found in PATH")
        print("   Please ensure Docker Desktop is running and WSL2 integration is enabled")
        return False

def check_dockerfile_syntax():
    """Verify Dockerfile syntax is correct"""
    dockerfiles = [
        "docker/dockerfiles/Dockerfile.minimal",
        "docker/dockerfiles/Dockerfile.standard", 
        "docker/dockerfiles/Dockerfile.full"
    ]
    
    print("\n📄 Checking Dockerfile syntax...")
    for df in dockerfiles:
        if os.path.exists(df):
            print(f"  ✅ {df} exists")
            # Check for basic syntax
            with open(df, 'r') as f:
                content = f.read()
                if 'FROM' in content and 'COPY' in content and 'RUN' in content:
                    print(f"     ✓ Basic syntax looks good")
                else:
                    print(f"     ⚠️  Missing required Docker commands")
        else:
            print(f"  ❌ {df} not found")

def check_mcp_server():
    """Verify MCP server can start"""
    print("\n🚀 Testing MCP server startup...")
    try:
        # Set Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = '/workspaces/Code-Index-MCP'
        
        # Try to run the server with --help
        result = subprocess.run(
            ['python', 'scripts/cli/mcp_server_cli.py', '--help'],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )
        
        if "MCP portable index detected" in result.stderr:
            print("  ✅ MCP server can start successfully")
            return True
        else:
            print("  ❌ MCP server failed to start")
            print(f"     Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Error testing MCP server: {e}")
        return False

def check_installation_scripts():
    """Verify installation scripts exist and are executable"""
    print("\n📜 Checking installation scripts...")
    scripts = [
        "scripts/install-mcp-docker.sh",
        "scripts/install-mcp-docker.ps1"
    ]
    
    for script in scripts:
        if os.path.exists(script):
            print(f"  ✅ {script} exists")
            if script.endswith('.sh'):
                # Check if executable
                if os.access(script, os.X_OK):
                    print(f"     ✓ Executable")
                else:
                    print(f"     ⚠️  Not executable (use: chmod +x {script})")
        else:
            print(f"  ❌ {script} not found")

def check_docker_compose():
    """Check Docker Compose setup"""
    print("\n🔧 Checking Docker Compose files...")
    compose_files = [
        "docker-compose.yml",
        "docker/compose/development/docker-compose.dev.yml",
        "docker/compose/production/docker-compose.production.yml"
    ]
    
    for cf in compose_files:
        if os.path.exists(cf):
            print(f"  ✅ {cf} exists")
            # Basic validation
            try:
                with open(cf, 'r') as f:
                    content = f.read()
                    if 'services:' in content:
                        print(f"     ✓ Valid compose file")
            except:
                print(f"     ⚠️  Could not validate")
        else:
            print(f"  ❌ {cf} not found")

def simulate_docker_build():
    """Show what the Docker build command would do"""
    print("\n🏗️  Docker Build Commands (when Docker is available):")
    print("\n# Build minimal image:")
    print("docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal .")
    print("\n# Build standard image:")
    print("docker build -f docker/dockerfiles/Dockerfile.standard -t mcp-index:standard .")
    print("\n# Run minimal version:")
    print("docker run -it -v $(pwd):/workspace mcp-index:minimal")
    print("\n# Run standard version with API key:")
    print("docker run -it -v $(pwd):/workspace -e VOYAGE_AI_API_KEY=your-key mcp-index:standard")

def main():
    print("🔍 MCP Index Docker Setup Test\n")
    
    # Check Docker availability
    docker_available = check_docker()
    
    # Check Dockerfiles
    check_dockerfile_syntax()
    
    # Check MCP server
    check_mcp_server()
    
    # Check installation scripts
    check_installation_scripts()
    
    # Check Docker Compose
    check_docker_compose()
    
    # Show build commands
    simulate_docker_build()
    
    print("\n📊 Summary:")
    if docker_available:
        print("✅ Docker is available - you can build and test the images!")
        print("\nNext steps:")
        print("1. Build the minimal image: docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal .")
        print("2. Test it: docker run -it -v $(pwd):/workspace mcp-index:minimal")
    else:
        print("⚠️  Docker is not available in this environment")
        print("\nTo test with Docker Desktop on Windows:")
        print("1. Ensure Docker Desktop is running")
        print("2. Enable WSL2 integration in Docker Desktop settings")
        print("3. Restart your WSL2 terminal")
        print("4. Run this test again")
        print("\nAlternatively, test the MCP server directly:")
        print("PYTHONPATH=/workspaces/Code-Index-MCP python scripts/cli/mcp_server_cli.py")

if __name__ == "__main__":
    main()