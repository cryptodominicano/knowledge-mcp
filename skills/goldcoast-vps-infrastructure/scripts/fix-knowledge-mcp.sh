#!/bin/bash
# Gold Coast VPS - Fix knowledge-mcp connectivity
# Run this when MCP can't reach Qdrant or Webtop

echo "=== Loading credentials ==="
source /root/.goldcoast_credentials 2>/dev/null || echo "Warning: No credentials file found"

echo "=== Getting current container IPs ==="
QDRANT_IP=$(docker inspect qdrant --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | cut -d' ' -f1)
WEBTOP_IP=$(docker inspect webtop --format '{{.NetworkSettings.Networks.bridge.IPAddress}}')

echo "Qdrant IP: $QDRANT_IP"
echo "Webtop IP: $WEBTOP_IP"

if [ -z "$QDRANT_IP" ] || [ -z "$WEBTOP_IP" ]; then
    echo "ERROR: Could not get IPs. Check if containers are running."
    exit 1
fi

echo ""
echo "=== Recreating knowledge-mcp ==="
docker stop knowledge-mcp 2>/dev/null
docker rm knowledge-mcp 2>/dev/null

docker run -d \
  --name knowledge-mcp \
  --restart unless-stopped \
  -p 8082:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e QDRANT_HOST=$QDRANT_IP \
  -e QDRANT_PORT=6333 \
  -e WEBTOP_API_URL=http://$WEBTOP_IP:5000 \
  --network bridge \
  knowledge-mcp

echo ""
echo "=== Installing Docker CLI ==="
sleep 3
docker exec knowledge-mcp sh -c "curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.0.3.tgz | tar xz -C /usr/local/bin --strip-components=1 docker/docker" 2>/dev/null

echo ""
echo "=== Testing connectivity ==="
sleep 2
echo -n "Qdrant: "
docker exec knowledge-mcp curl -s http://$QDRANT_IP:6333/collections | grep -q "ok" && echo "OK" || echo "FAILED"
echo -n "Webtop: "
docker exec knowledge-mcp curl -s http://$WEBTOP_IP:5000/status | grep -q "scrape" && echo "OK" || echo "FAILED"

echo ""
echo "=== Done! Refresh Claude.ai browser to reconnect ==="
