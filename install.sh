#!/bin/bash

# install.sh - Ratio Installation Script
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
RTO_DIR="$HOME/.rto"
SHELL_DIR="$RTO_DIR/shell"
BIN_DIR="$SHELL_DIR/bin"
KEYS_DIR="$RTO_DIR/keys"
FS_SYNC_SCRIPT="ratio_shell/bin/fs_sync"

# Default values
SKIP_DEPLOY=false
SYNC_FS=false
ENTITY_ID="admin"
DEPLOYMENT_ID="dev"
VERBOSE=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BOLD}${BLUE}$1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Install and configure Ratio"
    echo ""
    echo "Options:"
    echo "  --skip-deploy         Skip CDK deployment (deploy runs by default)"
    echo "  --entity-id ID        Entity ID for admin user (default: admin)"
    echo "  --deployment-id ID    Deployment ID (default: dev)"
    echo "  --sync-fs             Sync _fs directory to Ratio installation"
    echo "  --verbose             Show detailed output"
    echo "  --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Full install with defaults"
    echo "  $0 --skip-deploy                     # Install without deploying"
    echo "  $0 --entity-id myuser --verbose      # Custom entity with verbose output"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-deploy)
            SKIP_DEPLOY=true
            shift
            ;;
        --sync-fs)
            SYNC_FS=true
            shift
            ;;
        --entity-id)
            ENTITY_ID="$2"
            shift 2
            ;;
        --deployment-id)
            DEPLOYMENT_ID="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check for existing installation
check_existing_installation() {
    if [ -d "$RTO_DIR" ]; then
        print_success "Ratio is already configured at $RTO_DIR"
        echo ""
        echo "If you need to reconfigure, remove the directory first:"
        echo "  rm -rf $RTO_DIR"
        echo "  $0"
        exit 0
    fi
}

# Main installation function
main() {
    print_header "🚀 Ratio Installation"
    echo ""

    # Step 0: Check for existing installation
    check_existing_installation

    # Step 1: Validate rto command
    print_status "Checking for rto command..."
    if ! command_exists rto; then
        print_error "rto command not found!"
        echo ""
        echo "Please install the rto CLI first by running:"
        echo "  poetry install"
        echo ""
        echo "Then run this install script again."
        exit 1
    fi
    print_success "rto command found"

    # Step 2: CDK Deployment (optional)
    if [ "$SKIP_DEPLOY" = false ]; then
        print_status "Starting CDK deployment..."
        print_warning "This will take at least 20 minutes..."

        if [ "$VERBOSE" = true ]; then
            make deploy
        else
            print_status "Deploying infrastructure (this will take a while)..."
            make deploy > deploy.log 2>&1 || {
                print_error "CDK deployment failed. Check deploy.log for details."
                exit 1
            }
            rm -f deploy.log
        fi
        print_success "CDK deployment completed"
    else
        print_warning "Skipping CDK deployment (--skip-deploy specified)"
    fi

    # Step 3: Set up directories
    print_status "Setting up configuration directories..."
    mkdir -p "$RTO_DIR"
    mkdir -p "$SHELL_DIR"
    mkdir -p "$BIN_DIR"
    mkdir -p "$KEYS_DIR"
    print_success "Configuration directories created"

    # Step 4: Copy shell bin files
    print_status "Installing shell utilities..."

    if [ -d "ratio_shell/bin" ]; then
        cp -r ratio_shell/bin/* "$BIN_DIR/" 2>/dev/null || true

        # Make bin files executable
        find "$BIN_DIR" -type f -exec chmod +x {} \;

        print_success "Shell utilities installed to $BIN_DIR"

    else
        print_warning "ratio_shell/bin directory not found, skipping shell utilities"
    fi

    # Step 5: Initialize the system
    print_status "Initializing Ratio system..."

    # Run init command
    if rto --entity "$ENTITY_ID" init; then
        print_success "Ratio system initialized"

        # Move the generated private key to the .rto directory
        if [ -f "private_key.pem" ]; then
            FINAL_KEY_PATH="$KEYS_DIR/${ENTITY_ID}_priv_key.pem"
            mv "private_key.pem" "$FINAL_KEY_PATH"

            chmod 600 "$FINAL_KEY_PATH"

            print_success "Private key moved to $FINAL_KEY_PATH"

        else
            print_error "private_key.pem not found after initialization"

            exit 1
        fi

    else
        print_error "System initialization failed"

        exit 1
    fi

    # Step 6: Configure profile
    print_status "Configuring default profile..."

    rto configure \
        --name=default \
        --config-entity="$ENTITY_ID" \
        --config-deployment="$DEPLOYMENT_ID" \
        --config-key="$FINAL_KEY_PATH" \
        --set-default \
        --non-interactive

    print_success "Default profile configured"

    # Step 7: Test the installation
    print_status "Testing installation..."

    if rto pwd >/dev/null 2>&1; then
        print_success "Installation test passed"

    else
        print_error "Installation test failed"

        exit 1
    fi

    if [ "$SYNC_FS" = true ]; then
        print_status "Syncing _fs directory to Ratio installation..."

        if [ -f "$FS_SYNC_SCRIPT" ]; then
            # Run the filesystem sync script
            if bash "$FS_SYNC_SCRIPT" --executable-tools; then
                print_success "Filesystem sync completed successfully"

            else
                print_error "Filesystem sync failed"

                exit 1
            fi

        else
            print_error "Filesystem sync script not found: $FS_SYNC_SCRIPT"

            exit 1
        fi

    else
        print_warning "Skipping filesystem sync"
    fi

    # Installation complete
    echo ""
    print_header "🎉 Installation Complete!"
    echo ""
    print_success "Ratio has been successfully deployed and configured."
    echo ""
    echo "Configuration details:"
    echo "  • Profile: default"
    echo "  • Entity ID: $ENTITY_ID"
    echo "  • Deployment ID: $DEPLOYMENT_ID"
    echo "  • Config Directory: $RTO_DIR"
    echo "  • Shell Utilities: $BIN_DIR"
    echo ""
    echo "Getting started:"
    echo "  • Run 'rto --help' to see available commands"
    echo "  • Run 'rto pwd' to check your current directory"
    echo "  • Run 'rto ls' to list files"
    echo "  • Run './ratio_shell/execute' to start the interactive shell"
    echo ""

    print_success "Happy building with Ratio! 🚀"
}

# Trap to handle script interruption
trap 'echo ""; print_error "Installation interrupted by user"; exit 130' INT

# Run main function
main "$@"