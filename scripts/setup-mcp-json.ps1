# MCP.json Setup Script for Windows - Automatically configures MCP for your environment

param(
    [switch]$Interactive
)

# Color functions
function Write-Info { Write-Host "[INFO]" -ForegroundColor Blue -NoNewline; Write-Host " $args" }
function Write-Success { Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[WARN]" -ForegroundColor Yellow -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[ERROR]" -ForegroundColor Red -NoNewline; Write-Host " $args" }

# Detect environment
function Get-Environment {
    # Check if we're in a dev container
    if (Test-Path "/.dockerenv" -ErrorAction SilentlyContinue) {
        return "devcontainer"
    }
    
    # Check for Codespaces or Remote Containers
    if ($env:CODESPACES -or $env:REMOTE_CONTAINERS) {
        return "devcontainer"
    }
    
    # Check if Docker is available
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            # Test if Docker is actually running
            docker ps 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return "docker"
            } else {
                Write-Warn "Docker is installed but not running. Please start Docker Desktop."
            }
        }
    } catch {
        # Docker not available
    }
    
    # Check if we're in WSL
    if (Test-Path "/proc/version" -ErrorAction SilentlyContinue) {
        $version = Get-Content "/proc/version" -ErrorAction SilentlyContinue
        if ($version -match "microsoft") {
            if (Get-Command docker.exe -ErrorAction SilentlyContinue) {
                return "wsl-docker"
            } else {
                return "wsl"
            }
        }
    }
    
    # Windows with Docker Desktop
    if ($env:OS -eq "Windows_NT") {
        try {
            docker --version | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return "docker"
            }
        } catch {}
    }
    
    # Default to native
    return "native"
}

# Check for API key
function Test-ApiKey {
    if ($env:VOYAGE_AI_API_KEY) {
        Write-Success "Voyage AI API key detected"
        return $true
    }
    
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" -ErrorAction SilentlyContinue
        if ($envContent -match "VOYAGE_AI_API_KEY") {
            Write-Info "Voyage AI API key found in .env file"
            return $true
        }
    }
    
    Write-Warn "No Voyage AI API key found. Semantic search will be disabled."
    Write-Info "Get your free API key at: https://www.voyageai.com/"
    return $false
}

# Main setup function
function Set-McpJson {
    Write-Info "Detecting your environment..."
    
    $env = Get-Environment
    Write-Info "Detected environment: $env"
    
    # Map environment to template
    switch ($env) {
        "devcontainer" {
            $template = "native.json"
            Write-Info "Using native Python execution (already in container)"
        }
        "docker" {
            if (Test-ApiKey) {
                $template = "docker-standard.json"
                Write-Info "Using Docker with semantic search enabled"
            } else {
                $template = "docker-minimal.json"
                Write-Info "Using Docker minimal version (no API key)"
            }
        }
        "wsl-docker" {
            $template = "wsl-docker.json"
            Write-Info "Using Docker via WSL integration"
        }
        { $_ -in "wsl", "native" } {
            $template = "native.json"
            Write-Info "Using native Python execution"
        }
        default {
            $template = "auto-detect.json"
            Write-Warn "Unknown environment, using auto-detection"
        }
    }
    
    # Backup existing .mcp.json if it exists
    if (Test-Path ".mcp.json") {
        Write-Info "Backing up existing .mcp.json to .mcp.json.backup"
        Copy-Item ".mcp.json" ".mcp.json.backup" -Force
    }
    
    # Copy the appropriate template
    $templatePath = ".mcp.json.templates/$template"
    if (Test-Path $templatePath) {
        Copy-Item $templatePath ".mcp.json" -Force
        Write-Success "Created .mcp.json for $env environment"
    } else {
        Write-Error "Template not found: $templatePath"
        exit 1
    }
    
    # Show next steps
    Write-Host ""
    Write-Info "Next steps:"
    
    switch ($env) {
        { $_ -in "docker", "wsl-docker" } {
            Write-Host "1. Ensure Docker Desktop is running"
            Write-Host "2. Build the Docker image (if using local images):"
            Write-Host "   docker build -f docker/dockerfiles/Dockerfile.minimal -t mcp-index:minimal ."
            Write-Host "3. Open your project in Claude Code"
        }
        { $_ -in "devcontainer", "native", "wsl" } {
            Write-Host "1. Install dependencies (if not already done):"
            Write-Host "   pip install -e ."
            Write-Host "2. Open your project in Claude Code"
        }
    }
    
    if (-not (Test-ApiKey | Out-Null)) {
        Write-Host ""
        Write-Host "To enable semantic search:"
        Write-Host "1. Get an API key from https://www.voyageai.com/"
        Write-Host "2. Set it: `$env:VOYAGE_AI_API_KEY='your-key'"
        Write-Host "3. Re-run this script"
    }
}

# Interactive mode
function Start-InteractiveSetup {
    Write-Host "MCP.json Configuration Setup"
    Write-Host "============================"
    Write-Host ""
    Write-Host "Available configurations:"
    Write-Host "1. Auto-detect (recommended)"
    Write-Host "2. Docker - Minimal (no API key needed)"
    Write-Host "3. Docker - Standard (with semantic search)"
    Write-Host "4. Docker - Sidecar (for nested containers)"
    Write-Host "5. Native Python"
    Write-Host "6. WSL with Docker"
    Write-Host ""
    
    $choice = Read-Host "Select configuration (1-6) [1]"
    if ([string]::IsNullOrEmpty($choice)) { $choice = "1" }
    
    switch ($choice) {
        "1" { Set-McpJson }
        "2" { Copy-Item ".mcp.json.templates/docker-minimal.json" ".mcp.json" -Force }
        "3" { Copy-Item ".mcp.json.templates/docker-standard.json" ".mcp.json" -Force }
        "4" { Copy-Item ".mcp.json.templates/docker-sidecar.json" ".mcp.json" -Force }
        "5" { Copy-Item ".mcp.json.templates/native.json" ".mcp.json" -Force }
        "6" { Copy-Item ".mcp.json.templates/wsl-docker.json" ".mcp.json" -Force }
        default { 
            Write-Error "Invalid choice"
            exit 1
        }
    }
    
    Write-Success "Configuration complete!"
}

# Main execution
if ($Interactive) {
    Start-InteractiveSetup
} else {
    Set-McpJson
}