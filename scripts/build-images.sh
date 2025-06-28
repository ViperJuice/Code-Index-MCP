#!/bin/bash
# Local Docker Image Build Script
# Builds all MCP Docker image variants locally

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REGISTRY=${REGISTRY:-"mcp-index"}
TAG=${TAG:-"latest"}
PLATFORMS=${PLATFORMS:-"linux/amd64"}
PUSH=${PUSH:-false}

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --registry REGISTRY    Docker registry (default: mcp-index)"
    echo "  -t, --tag TAG              Image tag (default: latest)"
    echo "  -p, --platform PLATFORM    Build platform (default: linux/amd64)"
    echo "  -P, --push                 Push images to registry"
    echo "  -v, --variant VARIANT      Build specific variant (minimal|standard|full)"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Build all variants locally"
    echo "  $0"
    echo ""
    echo "  # Build and push to GitHub Container Registry"
    echo "  $0 --registry ghcr.io/code-index-mcp/mcp-index --push"
    echo ""
    echo "  # Build specific variant with custom tag"
    echo "  $0 --variant minimal --tag dev"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORMS="$2"
            shift 2
            ;;
        -P|--push)
            PUSH=true
            shift
            ;;
        -v|--variant)
            VARIANT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Function to build image
build_image() {
    local variant=$1
    local dockerfile="docker/dockerfiles/Dockerfile.${variant}"
    local image_name="${REGISTRY}:${TAG}-${variant}"
    
    echo -e "${YELLOW}Building ${variant} variant...${NC}"
    echo "  Dockerfile: ${dockerfile}"
    echo "  Image: ${image_name}"
    echo "  Platform: ${PLATFORMS}"
    
    if [ ! -f "$dockerfile" ]; then
        echo -e "${RED}Error: Dockerfile not found: ${dockerfile}${NC}"
        return 1
    fi
    
    # Build the image
    docker buildx build \
        --platform "${PLATFORMS}" \
        --file "${dockerfile}" \
        --tag "${image_name}" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --build-arg VERSION="${TAG}" \
        --build-arg VARIANT="${variant}" \
        --load \
        .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully built ${variant} variant${NC}"
        
        # Push if requested
        if [ "$PUSH" = true ]; then
            echo -e "${YELLOW}Pushing ${image_name}...${NC}"
            docker push "${image_name}"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Successfully pushed ${image_name}${NC}"
            else
                echo -e "${RED}✗ Failed to push ${image_name}${NC}"
                return 1
            fi
        fi
    else
        echo -e "${RED}✗ Failed to build ${variant} variant${NC}"
        return 1
    fi
    
    echo ""
}

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check for Docker Buildx
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}Error: Docker Buildx is not available${NC}"
    echo "Please update Docker or install buildx plugin"
    exit 1
fi

# Create or use buildx builder
BUILDER_NAME="mcp-builder"
if ! docker buildx ls | grep -q "${BUILDER_NAME}"; then
    echo -e "${YELLOW}Creating buildx builder: ${BUILDER_NAME}${NC}"
    docker buildx create --name "${BUILDER_NAME}" --use
else
    docker buildx use "${BUILDER_NAME}"
fi

# Print build configuration
echo -e "${GREEN}MCP Docker Image Builder${NC}"
echo "========================"
echo "Registry: ${REGISTRY}"
echo "Tag: ${TAG}"
echo "Platform: ${PLATFORMS}"
echo "Push: ${PUSH}"
echo ""

# Determine which variants to build
if [ -n "$VARIANT" ]; then
    # Build specific variant
    if [[ ! "$VARIANT" =~ ^(minimal|standard|full)$ ]]; then
        echo -e "${RED}Error: Invalid variant: ${VARIANT}${NC}"
        echo "Valid variants: minimal, standard, full"
        exit 1
    fi
    VARIANTS=("$VARIANT")
else
    # Build all variants
    VARIANTS=("minimal" "standard" "full")
fi

# Build images
echo -e "${YELLOW}Building ${#VARIANTS[@]} variant(s)...${NC}"
echo ""

FAILED_BUILDS=()
for variant in "${VARIANTS[@]}"; do
    if ! build_image "$variant"; then
        FAILED_BUILDS+=("$variant")
    fi
done

# Summary
echo "========================"
if [ ${#FAILED_BUILDS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All builds completed successfully!${NC}"
    echo ""
    echo "Images built:"
    for variant in "${VARIANTS[@]}"; do
        echo "  - ${REGISTRY}:${TAG}-${variant}"
    done
else
    echo -e "${RED}✗ Some builds failed:${NC}"
    for variant in "${FAILED_BUILDS[@]}"; do
        echo "  - ${variant}"
    done
    exit 1
fi

# Show image sizes
echo ""
echo "Image sizes:"
for variant in "${VARIANTS[@]}"; do
    docker images "${REGISTRY}:${TAG}-${variant}" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
done

# Cleanup builder if requested
if [ "$CLEANUP_BUILDER" = true ]; then
    echo ""
    echo -e "${YELLOW}Cleaning up buildx builder...${NC}"
    docker buildx rm "${BUILDER_NAME}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"