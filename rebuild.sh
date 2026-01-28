#!/bin/bash
# Rebuild knowledge-mcp container with latest agent.py

docker stop knowledge-mcp 2>/dev/null
docker rm knowledge-mcp 2>/dev/null

# Build new image from updated code
cd /root/knowledge-mcp
docker build -t knowledge-mcp . 2>/dev/null || {
    # If no Dockerfile, just copy to existing container
    echo "Using existing image, will copy agent.py after start"
}

# Run container with all env vars
docker run -d --name knowledge-mcp \
  --network root_default \
  -p 8082:8000 \
  -e QDRANT_HOST="172.17.0.2" \
  -e QDRANT_PORT=6333 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e WEBTOP_API_URL="http://webtop:5000" \
  -e WEBTOP_API_KEY="goldcoast2026" \
  -e N8N_API_KEY="$N8N_API_KEY" \
  -e N8N_BASE_URL="https://n8n.srv1175204.hstgr.cloud" \
  knowledge-mcp

# Connect to bridge network for Qdrant access
docker network connect bridge knowledge-mcp

# Copy latest agent.py
docker cp /root/knowledge-mcp/agent.py knowledge-mcp:/app/agent.py

# Restart to load new code
docker restart knowledge-mcp

echo "Knowledge-MCP rebuilt successfully"
