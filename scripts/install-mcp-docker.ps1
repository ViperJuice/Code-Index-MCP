# MCP Index Docker Installation Script for Windows
# PowerShell script to install and configure MCP Index with Docker

param(
    [string]$Variant = "minimal",
    [string]$Version = "latest"
)

# Configuration
$MCPRegistry = "ghcr.io"
$MCPImage = "$MCPRegistry/code-index-mcp/mcp-index"
$ErrorActionPreference = "Stop"

# Colors
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Print-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║        MCP Index Docker Installer         ║" -ForegroundColor Blue
    Write-Host "║   Fast, local-first code indexing tool    ║" -ForegroundColor Blue
    Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Docker {
    try {
        $dockerVersion = docker --version
        Write-Host "[INFO] Docker is installed: $dockerVersion" -ForegroundColor Green
        return $true
    }
    catch {
        return $false
    }
}

function Install-Docker {
    Write-Host "[WARN] Docker is not installed" -ForegroundColor Yellow
    
    $response = Read-Host "Would you like to install Docker Desktop? (y/N)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "[ERROR] Docker is required for MCP Index" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
        exit 1
    }
    
    Write-Host "[INFO] Downloading Docker Desktop installer..." -ForegroundColor Green
    $installerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $installerPath = "$env:TEMP\DockerDesktopInstaller.exe"
    
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
        Write-Host "[INFO] Starting Docker Desktop installation..." -ForegroundColor Green
        Start-Process -FilePath $installerPath -ArgumentList "install", "--quiet" -Wait
        
        Write-Host "[INFO] Docker Desktop installed successfully" -ForegroundColor Green
        Write-Host "[WARN] Please restart your computer to complete the installation" -ForegroundColor Yellow
        exit 0
    }
    catch {
        Write-Host "[ERROR] Failed to install Docker Desktop: $_" -ForegroundColor Red
        Write-Host "Please install manually from: https://www.docker.com/products/docker-desktop/"
        exit 1
    }
}

function Select-Variant {
    Write-Host ""
    Write-Host "Choose MCP Index variant:"
    Write-Host "1) minimal  - Zero configuration, BM25 search only (recommended for start)"
    Write-Host "2) standard - AI-powered semantic search (requires Voyage AI key)"
    Write-Host "3) full     - Production stack with monitoring"
    Write-Host ""
    
    $choice = Read-Host "Select variant [1-3] (default: 1)"
    
    switch ($choice) {
        "2" {
            $script:Variant = "standard"
            Write-Host "[INFO] Selected: standard (semantic search)" -ForegroundColor Green
            
            # Check for API key
            if (-not $env:VOYAGE_AI_API_KEY) {
                Write-Host "[WARN] Semantic search requires a Voyage AI API key" -ForegroundColor Yellow
                Write-Host "Get your free API key at: https://www.voyageai.com/"
                Write-Host "Pricing: ~`$0.05 per 1M tokens (free tier: 50M tokens/month)"
                Write-Host ""
                
                $apiKey = Read-Host "Enter your Voyage AI API key (or press Enter to skip)"
                if ($apiKey) {
                    [Environment]::SetEnvironmentVariable("VOYAGE_AI_API_KEY", $apiKey, "User")
                    $env:VOYAGE_AI_API_KEY = $apiKey
                    Write-Host "[INFO] API key saved to user environment" -ForegroundColor Green
                }
            }
        }
        "3" {
            $script:Variant = "full"
            Write-Host "[INFO] Selected: full (production stack)" -ForegroundColor Green
        }
        default {
            $script:Variant = "minimal"
            Write-Host "[INFO] Selected: minimal (zero configuration)" -ForegroundColor Green
        }
    }
}

function Pull-Image {
    $imageTag = "${MCPImage}:${Variant}"
    Write-Host "[INFO] Pulling MCP Index image: $imageTag" -ForegroundColor Green
    docker pull $imageTag
}

function Create-Launcher {
    $launcherContent = @'
@echo off
REM MCP Index Docker Launcher for Windows

SET MCP_VARIANT=%MCP_VARIANT%
IF "%MCP_VARIANT%"=="" SET MCP_VARIANT=minimal

SET MCP_IMAGE=ghcr.io/code-index-mcp/mcp-index
SET WORKSPACE=%CD%

IF "%1"=="setup" (
    echo Running MCP Index setup wizard...
    docker run -it --rm -v "%WORKSPACE%:/workspace" %MCP_IMAGE%:%MCP_VARIANT% --setup
    EXIT /B
)

IF "%1"=="upgrade" (
    echo Upgrading MCP Index...
    docker pull %MCP_IMAGE%:%MCP_VARIANT%
    EXIT /B
)

REM Run MCP server with all arguments
docker run -i --rm ^
    -v "%WORKSPACE%:/workspace" ^
    -v "%USERPROFILE%\.mcp-index:/app/.mcp-index" ^
    -e VOYAGE_AI_API_KEY=%VOYAGE_AI_API_KEY% ^
    -e MCP_ARTIFACT_SYNC=%MCP_ARTIFACT_SYNC% ^
    %MCP_IMAGE%:%MCP_VARIANT% %*
'@

    $launcherPath = "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\mcp-index.bat"
    
    # Create directory if it doesn't exist
    $launcherDir = Split-Path $launcherPath -Parent
    if (-not (Test-Path $launcherDir)) {
        New-Item -ItemType Directory -Path $launcherDir -Force | Out-Null
    }
    
    # Write the launcher
    Set-Content -Path $launcherPath -Value $launcherContent -Encoding ASCII
    
    Write-Host "[INFO] Launcher installed at: $launcherPath" -ForegroundColor Green
    
    # Add to PATH if not already there
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$launcherDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$launcherDir", "User")
        Write-Host "[INFO] Added to PATH (restart terminal to use 'mcp-index' command)" -ForegroundColor Green
    }
}

function Create-MCPJson {
    $mcpConfig = @{
        mcpServers = @{
            "code-index" = @{
                command = "docker"
                args = @(
                    "run", 
                    "-i", 
                    "--rm",
                    "-v", "`${workspace}:/workspace",
                    "-v", "`${USERPROFILE}\.mcp-index:/app/.mcp-index",
                    "-e", "VOYAGE_AI_API_KEY=`${VOYAGE_AI_API_KEY:-}",
                    "-e", "MCP_ARTIFACT_SYNC=`${MCP_ARTIFACT_SYNC:-true}",
                    "${MCPImage}:${Variant}"
                )
            }
        }
    } | ConvertTo-Json -Depth 10
    
    Set-Content -Path ".mcp.json" -Value $mcpConfig
    Write-Host "[INFO] Created .mcp.json for Claude Code integration" -ForegroundColor Green
}

function Show-NextSteps {
    Write-Host ""
    Write-Host "✅ MCP Index Docker installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "1. Restart your terminal"
    Write-Host "2. Test the installation:"
    Write-Host "   mcp-index --version"
    Write-Host ""
    Write-Host "3. Index your current directory:"
    Write-Host "   mcp-index"
    Write-Host ""
    
    if ($Variant -eq "standard" -or $Variant -eq "full") {
        Write-Host "4. Configure semantic search:"
        Write-Host "   `$env:VOYAGE_AI_API_KEY = 'your-key-here'"
        Write-Host "   Get your key at: https://www.voyageai.com/"
        Write-Host ""
    }
    
    Write-Host "5. For Claude Code integration:"
    Write-Host "   - Copy .mcp.json to your project root"
    Write-Host "   - Claude will automatically use the Docker version"
    Write-Host ""
    Write-Host "Documentation: https://github.com/Code-Index-MCP/docs/DOCKER_GUIDE.md"
}

# Main installation flow
Print-Banner

# Check if running as administrator (not required but recommended)
if (-not (Test-Administrator)) {
    Write-Host "[WARN] Running without administrator privileges" -ForegroundColor Yellow
    Write-Host "Some features may require administrator access" -ForegroundColor Yellow
}

# Check Docker
if (-not (Test-Docker)) {
    Install-Docker
}

# Select variant
Select-Variant

# Pull image
Pull-Image

# Create launcher
Create-Launcher

# Create .mcp.json
Create-MCPJson

# Show next steps
Show-NextSteps