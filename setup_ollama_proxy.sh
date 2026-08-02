#!/bin/bash
set -e

echo "Installing socat..."
sudo apt-get install -y socat

echo "Creating ollama-proxy systemd service..."
sudo tee /etc/systemd/system/ollama-proxy.service > /dev/null <<EOF
[Unit]
Description=Ollama Docker bridge
After=network.target

[Service]
ExecStart=/usr/bin/socat TCP-LISTEN:11434,bind=172.17.0.1,fork TCP:127.0.0.1:11434
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ollama-proxy
sudo systemctl start ollama-proxy

echo "Done! Checking status..."
sudo systemctl status ollama-proxy --no-pager
