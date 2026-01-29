---
name: goldcoast-vps-infrastructure
description: Troubleshoot Gold Coast AI Automations VPS infrastructure including Docker networking, MCP connections, Qdrant, Webtop API, and N8N. Use when encountering MCP disconnections, "Connection refused" errors, "Name or service not known" errors, container networking issues, or need to restart/fix knowledge-mcp, webtop API, or related services on srv1175204.hstgr.cloud.
---

# Gold Coast VPS Infrastructure Skill

## Tech Stack

### Infrastructure
| Component | Version | Purpose |
|-----------|---------|---------|
| Ubuntu | 24.04.3 LTS | Host OS |
| Docker | 29.1.5 | Container runtime |
| Traefik | 3.6.2 | Reverse proxy, SSL |

### MCP Stack
| Component | Version | Purpose |
|-----------|---------|---------|
| FastMCP | 2.14.4 | MCP server framework |
| Uvicorn | 0.40.0 | ASGI server |
| SSE Transport | - | Claude connection |

### Python Stack
| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.12.3 | Runtime |
| Flask | 3.x | REST APIs |
| SeleniumBase | 4.46.0 | Stealth scraping |
| Selenium | 4.40.0 | Browser automation |
| OpenAI SDK | 2.15.0 | Embeddings, GPT |
| Qdrant Client | 1.16.2 | Vector DB client |
| HTTPX | 0.28.1 | Async HTTP |

### Databases
| Database | Version | Purpose |
|----------|---------|---------|
| Qdrant | 1.16.3 | Vector DB (embeddings) |
| PostgreSQL | 15, 16 | Relational (Cal.com, Twenty) |
| Redis | 7-alpine | Caching (Twenty) |

### Automation & Workflow
| Tool | Version | Purpose |
|------|---------|---------|
| N8N | 1.122.4 | Workflow automation |
| Apify | Cloud | Scraping orchestration |
| Instantly.ai | Cloud | Cold email |

### AI/LLM Services
| Service | Purpose |
|---------|---------|
| OpenAI | GPT-4o, embeddings |
| Anthropic Claude | AI assistance |
| Groq | Fast inference (Llama 3.3) |
| Google Gemini | Alternative LLM |
| ElevenLabs | Voice synthesis |
| AssemblyAI | Transcription |

### Business Tools
| Tool | Purpose |
|------|---------|
| Cal.com | Scheduling |
| Twenty CRM | Customer management |
| Botpress v12 | Chatbots |
| Code Server | Web IDE |

### External APIs
| API | Purpose |
|-----|---------|
| Keepa | Amazon price tracking |
| GoDaddy | Domain availability |
| Cloudinary | Image CDN |
| Meta WhatsApp | Messaging |

## Network Architecture

### Docker Networks
| Network | Purpose |
|---------|---------|
| `bridge` | Qdrant, MCPs, Webtop |
| `root_default` | N8N, Traefik, Cal.com |

### Container IPs (verify on restart)
| Container | Bridge IP | Port |
|-----------|-----------|------|
| qdrant | 172.17.0.2 | 6333 |
| botpress-mcp | 172.17.0.3 | 8080→8000 |
| knowledge-mcp | 172.17.0.4 | 8082→8000 |
| webtop | 172.17.0.5 | 5000 |
| root-n8n-1 | 172.18.0.6 | 5678 |

```
┌─────────────────────────────────────────────────────────────┐
│                    BRIDGE NETWORK                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Qdrant  │  │knowledge│  │botpress │  │     Webtop      │ │
│  │ :6333   │  │  -mcp   │  │  -mcp   │  │ (Chrome, Python)│ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   ROOT_DEFAULT NETWORK                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Traefik │  │   N8N   │  │ Cal.com │  │   Twenty CRM    │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**CRITICAL:** IPs change on restart! Verify with:
```bash
docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}'
```

## knowledge-mcp Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY       # For embeddings
QDRANT_HOST          # Qdrant IP
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

| Issue | Cause | Fix |
|-------|-------|-----|
| "Name or service not known" | Wrong network | Use IPs, not hostnames |
| "Connection refused" | Container unreachable | Check IPs, recreate MCP |
| "OpenAI not configured" | Missing env var | Add OPENAI_API_KEY |
| Docker commands fail | No CLI | Install Docker CLI |
| Claude can't connect | Stale SSE | Refresh browser |

## Quick Diagnostic
```bash
# Check IPs
for c in qdrant webtop knowledge-mcp botpress-mcp; do
  echo -n "$c: "
  docker inspect $c --format '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' 2>/dev/null || echo "not running"
done

# Test connectivity
docker exec knowledge-mcp curl -s http://172.17.0.2:6333/collections
docker exec knowledge-mcp curl -s http://172.17.0.5:5000/status

# Check logs
docker logs knowledge-mcp --tail 30
```

## Credentials

Location: `/root/.goldcoast_credentials` (chmod 600)
Load: `source /root/load_credentials.sh`

| Category | Variables |
|----------|-----------|
| AI/LLM | OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, GOOGLE_GEMINI_KEY, ELEVENLABS_API_KEY, ASSEMBLY_AI_KEY |
| Domains | GODADDY_API_KEY, GODADDY_API_SECRET |
| Automation | APIFY_TOKEN, INSTANTLY_API_KEY, KEEPA_API_KEY |
| Google | GMAIL_CLIENT_ID, GOOGLE_CLOUD_CLIENT_ID |
| Cal.com | CALCOM_LICENSE_KEY, CAL_API_KEY, CAL_SIGNATURE_TOKEN |
| WhatsApp | META_WHATSAPP_TOKEN, META_USER_TOKEN |
| CRM | TWENTY_CRM_API_KEY, ATLASSIAN_API_KEY |
| Media | CLOUDINARY_KEY, CLOUDINARY_SECRET |

## Key URLs

| Service | URL |
|---------|-----|
| N8N | https://n8n.srv1175204.hstgr.cloud |
| Cal.com | https://cal.srv1175204.hstgr.cloud |
| Webtop | https://webtop.srv1175204.hstgr.cloud |
| Botpress | https://botpress.srv1175204.hstgr.cloud |

## Key Paths

| Item | Path |
|------|------|
| Credentials | `/root/.goldcoast_credentials` |
| Fix Scripts | `/root/vps-scripts/` |
| BookDepot API | `/config/bookdepot_api.py` |
| Scraper | `/config/bookdepot_scraper.py` |
| Python Env | `/config/scraper-env/bin/python` |

## GitHub Repos

- https://github.com/cryptodominicano/knowledge-mcp
- https://github.com/cryptodominicano/bookdepot-analyzer
