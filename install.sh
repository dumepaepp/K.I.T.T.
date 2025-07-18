#!/bin/bash

# ==============================================================================
# Automated Installer for the AI Agent Project
#
# This script installs all necessary dependencies:
# 1. System tools (Nmap, Aircrack-ng) based on OS detection.
# 2. The Ollama server.
# 3. The WhiteRabbitNeo AI model.
# 4. Required Python libraries via pip.
#
# USAGE:
#   1. Save this script as `install.sh`.
#   2. Make it executable: `chmod +x install.sh`
#   3. Run it: `./install.sh`
#   4. On Linux, you might be prompted for your sudo password.
# ==============================================================================

# --- Helper Functions ---
echo_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

echo_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

echo_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

echo_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main Installation Logic ---

# 1. Install System Dependencies (Nmap & Aircrack-ng)
echo_info "Checking for and installing system dependencies (Nmap, Aircrack-ng)..."

# Using a more robust check to avoid shell parsing issues.
nmap_found=false
aircrack_found=false
if command_exists nmap; then nmap_found=true; fi
if command_exists aircrack-ng; then aircrack_found=true; fi

if $nmap_found && $aircrack_found; then
    echo_success "Nmap and Aircrack-ng are already installed."
else
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        if ! command_exists brew; then
            echo_error "Homebrew not found. Please install it from https://brew.sh/ then re-run this script."
            exit 1
        fi
        echo_info "Detected macOS. Installing with Homebrew..."
        brew install nmap aircrack-ng
    elif [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo_info "Detected Debian/Ubuntu. Installing with apt-get..."
        sudo apt-get update
        sudo apt-get install -y nmap aircrack-ng
    elif [ -f /etc/redhat-release ]; then
        # Fedora/CentOS/RHEL
        echo_info "Detected Fedora/RHEL based system. Installing with dnf..."
        sudo dnf install -y nmap aircrack-ng
    else
        echo_error "Unsupported operating system. Please install Nmap and Aircrack-ng manually."
        exit 1
    fi

    if ! command_exists nmap || ! command_exists aircrack-ng; then
        echo_error "Installation of system dependencies failed. Please try installing them manually."
        exit 1
    else
        echo_success "System dependencies installed successfully."
    fi
fi

# 2. Install Ollama
echo_info "Checking for and installing Ollama..."
if command_exists ollama; then
    echo_success "Ollama is already installed."
else
    echo_info "Downloading and running the official Ollama installer..."
    curl -fsSL https://ollama.com/install.sh | sh
    if ! command_exists ollama; then
        echo_error "Ollama installation failed. Please try installing it manually from https://ollama.com/"
        exit 1
    fi
    echo_success "Ollama installed successfully."
fi

# 3. Pull the WhiteRabbitNeo model
echo_info "Pulling the WhiteRabbitNeo model. This may take a significant amount of time and disk space..."
# The `ollama list` command is a good way to check if a model exists.
# We pipe the output to grep to search for the model name.
if ollama list | grep -q "whiterabbitneo/whiterabbitneo-33b"; then
    echo_success "WhiteRabbitNeo model is already available."
else
    ollama pull whiterabbitneo/whiterabbitneo-33b
    echo_success "WhiteRabbitNeo model pulled successfully."
fi


# 4. Install Python Dependencies
echo_info "Installing required Python libraries via pip..."
if ! command_exists pip && ! command_exists pip3; then
    echo_error "pip/pip3 not found. Please install Python and pip, then re-run this script."
    exit 1
fi

# Use pip3 if available, otherwise fall back to pip
PIP_CMD=$(command -v pip3 || command -v pip)
$PIP_CMD install langchain langchain-community duckduckgo-search

echo_success "Python libraries installed successfully."


# --- Final Instructions ---
echo_info "------------------------------------------------------------------"
echo_success "All dependencies have been installed!"
echo_info "You can now run the main application using:"
echo
echo "    python3 main.py"
echo
echo_warning "REMINDER: For full functionality of Nmap and Aircrack-ng, you may need to run the script with root privileges:"
echo_warning "    sudo python3 main.py"
echo_info "------------------------------------------------------------------"

