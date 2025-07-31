#LLM Installation Script for Linode
#!/bin/bash

# --- Script to install text-generation-webui and a model on a Linode instance ---

# Stop on any error
set -e

echo "--- Starting LLM Server Setup ---"

# 1. Update and install dependencies
echo "[INFO] Updating package lists and installing dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv

# 2. Clone the text-generation-webui repository
echo "[INFO] Cloning the text-generation-webui repository..."
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui

# 3. Set up Python virtual environment
echo "[INFO] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python requirements
echo "[INFO] Installing Python requirements. This will take some time..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Download the LLM (e.g., WhiteRabbitNeo-33B-GGUF)
# You can replace this with any other GGUF model from Hugging Face.
echo "[INFO] Downloading the LLM model..."
# This is a quantized version, suitable for CPU or less powerful GPUs.
# For full performance on a powerful GPU, you would download the full model.
wget https://huggingface.co/TheBloke/WhiteRabbitNeo-33B-GGUF/resolve/main/whiterabbitneo-33b.Q4_K_M.gguf -O models/whiterabbitneo-33b.Q4_K_M.gguf

# 6. Start the server
echo "[INFO] Starting the web server..."
echo "----------------------------------------------------------------"
echo "The server is about to start."
echo "Once it's running, you can access the UI from your browser at http://<your-linode-ip>:7860"
echo "The API will be available at http://<your-linode-ip>:5000/v1"
echo "Update the Pentest Assistant settings with this API URL."
echo "----------------------------------------------------------------"

# --listen: Makes it accessible from your public IP
# --model: Specifies the model to load
# --api: Enables the OpenAI-compatible API
python server.py --listen --model whiterabbitneo-33b.Q4_K_M.gguf --api

echo "--- Setup Complete ---"

