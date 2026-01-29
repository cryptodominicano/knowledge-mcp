#!/bin/bash
# Gold Coast VPS - Full diagnostic

echo "=========================================="
echo "  GOLD COAST VPS DIAGNOSTIC"
echo "  $(date)"
echo "=========================================="

echo ""
echo "=== DOCKER CONTAINERS ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -15

echo ""
echo "=== CONTAINER IPs ==="
for c in qdrant webtop knowledge-mcp botpress-mcp root-n8n-1; do
  IP=$(docker inspect $c --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null)
  if [ -n "$IP" ]; then
    echo "$c: $IP"
  else
    echo "$c: NOT RUNNING"
  fi
done

echo ""
echo "=== WEBTOP API STATUS ==="
WEBTOP_IP=$(docker inspect webtop --format '{{.NetworkSettings.Networks.bridge.IPAddress}}' 2>/dev/null)
if [ -n "$WEBTOP_IP" ]; then
  curl -s http://$WEBTOP_IP:5000/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Scrape: {\"RUNNING\" if d[\"scrape\"][\"running\"] else \"idle\"}'); print(f'Analyze: {\"RUNNING\" if d[\"analyze\"][\"running\"] else \"idle\"}')" 2>/dev/null || echo "API not responding"
else
  echo "Webtop not running"
fi

echo ""
echo "=== QDRANT STATUS ==="
QDRANT_IP=$(docker inspect qdrant --format '{{.NetworkSettings.Networks.bridge.IPAddress}}' 2>/dev/null)
if [ -n "$QDRANT_IP" ]; then
  curl -s http://$QDRANT_IP:6333/collections 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}'); print(f'Collections: {len(d[\"result\"][\"collections\"])}')" 2>/dev/null || echo "Qdrant not responding"
else
  echo "Qdrant not running"
fi

echo ""
echo "=== KNOWLEDGE-MCP STATUS ==="
docker logs knowledge-mcp --tail 5 2>/dev/null | grep -E "INFO|ERROR" || echo "No recent logs"

echo ""
echo "=== MCP SSE ENDPOINT ==="
timeout 2 curl -s http://localhost:8082/sse 2>/dev/null | head -2 || echo "MCP not responding on 8082"

echo ""
echo "=========================================="
