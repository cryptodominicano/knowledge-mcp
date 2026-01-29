---
name: goldcoast-vps-infrastructure
description: Troubleshoot Gold Coast AI Automations VPS infrastructure including Docker networking, MCP connections, Qdrant, Webtop API, and N8N. Use when encountering MCP disconnections, "Connection refused" errors, "Name or service not known" errors, container networking issues, or need to restart/fix knowledge-mcp, webtop API, or related services on srv1175204.hstgr.cloud.
---

# Gold Coast VPS Infrastructure Skill

## Overview
This skill documents the complete Docker infrastructure for Gold Coast AI Automations on Hostinger VPS (srv1175204.hstgr.cloud). Use this when troubleshooting MCP connections, network issues, or container communication failures.

## Network Architecture

### Docker Networks
| Network | ID | Purpose |
|---------|-----|---------|
| `bridge` | 8661b5ddd64d | Default Docker network - **Qdrant, MCPs, Webtop** |
| `root_default` | 340aeabe09b1 | Docker Compose network - **N8N, Traefik, Cal.com** |

### Container IPs (as of Jan 2026)
| Container | Bridge IP | root_default IP | Port |
|-----------|-----------|-----------------|------|
| qdrant | 172.17.0.2 | - | 6333 |
| botpress-mcp | 172.17.0.3 | - | 8080→8000 |
| knowledge-mcp | 172.17.0.4 | - | 8082→8000 |
| webtop | 172.17.0.5 | 172.18.0.12 | 5000 (API) |
| root-n8n-1 | - | 172.18.0.6 | 5678 |

**CRITICAL:** IPs may change on container restart! Always verify with:
```bash
docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
```

## knowledge-mcp Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY       # For embeddings (from /root/.goldcoast_credentials)
QDRANT_HOST          # Qdrant IP on bridge network
QDRANT_PORT          # 6333
WEBTOP_API_URL       # http://<webtop-ip>:5000
```

### Full Docker Run Command
```bash
source /root/.goldcoast_credentials
QDRANT_IP=$(docker inspect qdrant --format '{{.NetworkSettings.Networks.bridge.IPAddress}}')
WEBTOP_IP=$(docker inspect webtop --format '{{.NetworkSettings.Networks.bridge.IPAddress}}')

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
```

### Post-Creation: Install Docker CLI
```bash
docker exec knowledge-mcp sh -c "curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.0.3.tgz | tar xz -C /usr/local/bin --strip-components=1 docker/docker"
```

## Common Issues & Fixes

### Issue 1: "Name or service not known" / Can't resolve hostnames
**Cause:** Containers on different networks can't resolve each other by name.
**Fix:** Use IP addresses instead of hostnames, ensure all containers on `bridge` network.

### Issue 2: "[Errno 111] Connection refused" from knowledge-mcp
**Cause:** Qdrant or Webtop not reachable.
**Diagnostic:**
```bash
docker exec knowledge-mcp curl -s http://172.17.0.2:6333/collections
docker exec knowledge-mcp curl -s http://172.17.0.5:5000/status
```

### Issue 3: "OpenAI not configured" error
**Cause:** OPENAI_API_KEY not set in container.
**Fix:** Recreate container with OPENAI_API_KEY from credentials file.

### Issue 4: Docker commands fail inside knowledge-mcp
**Fix:** Install Docker CLI (see Post-Creation above)

### Issue 5: Claude.ai can't connect to MCP after container restart
**Fix:** Refresh the browser page to reconnect Claude to MCP.

## Quick Diagnostic Commands
```bash
# Check all container IPs
for c in qdrant webtop knowledge-mcp botpress-mcp root-n8n-1; do
  echo -n "$c: "
  docker inspect $c --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null || echo "not running"
done

# Test knowledge-mcp connectivity
docker exec knowledge-mcp curl -s http://172.17.0.5:5000/status
docker exec knowledge-mcp curl -s http://172.17.0.2:6333/collections

# Check MCP logs
docker logs knowledge-mcp --tail 30
```

## Credentials Management

All API keys stored securely at `/root/.goldcoast_credentials` (chmod 600).

### Loading Credentials
```bash
source /root/load_credentials.sh
```

### Available Credentials
| Category | Variable | Service |
|----------|----------|---------|
| **AI/LLM** | OPENAI_API_KEY | OpenAI (embeddings, GPT) |
| | ANTHROPIC_API_KEY | Claude API |
| | GROQ_API_KEY | Groq (Llama models) |
| | GOOGLE_GEMINI_KEY | Google Gemini 2.5 |
| | ELEVENLABS_API_KEY | Voice synthesis |
| | ASSEMBLY_AI_KEY | Transcription |
| **Domains** | GODADDY_API_KEY | Domain availability |
| **Automation** | APIFY_TOKEN | Web scraping |
| | INSTANTLY_API_KEY | Cold email |
| | KEEPA_API_KEY | Amazon price tracking |
| **Google** | GMAIL_CLIENT_ID | Gmail API |
| | GOOGLE_CLOUD_CLIENT_ID | Google Cloud |
| **Cal.com** | CALCOM_LICENSE_KEY | Scheduling |
| | CAL_API_KEY | |
| **WhatsApp** | META_WHATSAPP_TOKEN | WhatsApp Business API |
| **CRM** | TWENTY_CRM_API_KEY | Twenty CRM |
| | ATLASSIAN_API_KEY | Jira/Confluence |
| **Media** | CLOUDINARY_KEY | Image hosting |
| **Internal** | WEBTOP_API_KEY | BookDepot API |

## Webtop BookDepot API

### Starting the API
```bash
docker exec -d webtop bash -c "cd /config && KEEPA_API_KEY=\$KEEPA_API_KEY /config/scraper-env/bin/python /config/bookdepot_api.py"
```

### API Files
- `/config/bookdepot_api.py` - Flask API server
- `/config/bookdepot_scraper.py` - BookDepot scraper
- `/config/keepa_analyzer.py` - Keepa profit analyzer

## GitHub Backup

BookDepot analyzer: `https://github.com/cryptodominicano/bookdepot-analyzer`
Knowledge MCP: `https://github.com/cryptodominicano/knowledge-mcp`

## Key Paths

| Item | Path |
|------|------|
| Credentials File | `/root/.goldcoast_credentials` |
| Credentials Loader | `/root/load_credentials.sh` |
| VPS Fix Scripts | `/root/vps-scripts/` |
| Webtop Python | `/config/scraper-env/bin/python` |
