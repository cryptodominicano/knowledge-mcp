# Gold Coast AI Automations - Tech Stack

**VPS:** Hostinger VPS (srv1175204.hstgr.cloud)  
**Last Updated:** January 2026

---

## 🖥️ Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| **Ubuntu** | 24.04.3 LTS (Noble Numbat) | Host OS |
| **Docker** | 29.1.5 | Container runtime |
| **Docker Compose** | v2 (integrated) | Multi-container orchestration |

---

## 🔄 Automation & Workflow

| Tool | Version | Purpose |
|------|---------|---------|
| **N8N** | 1.122.4 | Workflow automation, webhooks |
| **Apify** | Cloud API | Web scraping orchestration |
| **Instantly.ai** | Cloud API | Cold email campaigns |

---

## 🤖 AI/LLM Services

| Service | Model/Version | Purpose |
|---------|---------------|---------|
| **OpenAI** | GPT-4o, text-embedding-3-small | Chat, embeddings |
| **Anthropic Claude** | Claude 3.5 Sonnet | AI assistance, coding |
| **Groq** | Llama 3.3 70B | Fast inference fallback |
| **Google Gemini** | 2.5 Flash | Alternative LLM |
| **ElevenLabs** | API | Voice synthesis |
| **AssemblyAI** | API | Audio transcription |

---

## 🗄️ Databases & Storage

| Database | Version | Purpose |
|----------|---------|---------|
| **Qdrant** | 1.16.3 | Vector database (embeddings, semantic search) |
| **PostgreSQL** | 15, 16 | Relational DB (Cal.com, Twenty CRM) |
| **Redis** | 7-alpine | Caching (Twenty CRM) |

---

## 🌐 Web & Networking

| Component | Version | Purpose |
|-----------|---------|---------|
| **Traefik** | 3.6.2 | Reverse proxy, SSL termination |

---

## 🐍 Python Stack

| Package | Version | Purpose |
|---------|---------|---------|
| **Python** | 3.12.3 | Runtime |
| **FastMCP** | 2.14.4 | MCP server framework |
| **Uvicorn** | 0.40.0 | ASGI server |
| **Flask** | 3.x | REST API (BookDepot) |
| **SeleniumBase** | 4.46.0 | Stealth web scraping |
| **Selenium** | 4.40.0 | Browser automation |
| **OpenAI SDK** | 2.15.0 | OpenAI API client |
| **Qdrant Client** | 1.16.2 | Vector DB client |
| **HTTPX** | 0.28.1 | Async HTTP client |

---

## 💬 Chatbots & Communication

| Tool | Version | Purpose |
|------|---------|---------|
| **Botpress** | v12 (self-hosted) | Chatbot platform |
| **WhatsApp Business API** | Meta Cloud | Messaging channel |
| **Twilio** | API | Voice/SMS |

---

## 📅 Business Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Cal.com** | Latest (self-hosted) | Scheduling |
| **Twenty CRM** | Latest (self-hosted) | Customer relationship management |
| **Code Server** | Latest | Web-based VS Code |

---

## 🖼️ Desktop & GUI

| Tool | Image | Purpose |
|------|-------|---------|
| **Webtop** | linuxserver/webtop:ubuntu-xfce | Remote desktop for browser automation |

---

## 🔌 MCP Servers (Model Context Protocol)

| Server | Port | Purpose |
|--------|------|---------|
| **knowledge-mcp** | 8082 | Qdrant KB, exec commands, file ops |
| **botpress-mcp** | 8080 | Botpress bot management, git ops |

### MCP Stack
```
FastMCP 2.14.4 → Uvicorn 0.40.0 → SSE Transport → Claude Desktop/Web
```

---

## 📦 Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BRIDGE NETWORK                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Qdrant  │  │knowledge│  │botpress │  │     Webtop      │ │
│  │ :6333   │  │  -mcp   │  │  -mcp   │  │ (Chrome, Python)│ │
│  │         │  │ :8082   │  │ :8080   │  │     :5000       │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   ROOT_DEFAULT NETWORK                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │ Traefik │  │   N8N   │  │ Cal.com │  │   Twenty CRM    │ │
│  │  :443   │  │  :5678  │  │         │  │                 │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                      │
│  │Postgres │  │Postgres │  │  Redis  │                      │
│  │  :5432  │  │  :5433  │  │  :6379  │                      │
│  │(Cal.com)│  │(Twenty) │  │(Twenty) │                      │
│  └─────────┘  └─────────┘  └─────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 External APIs

| API | Purpose |
|-----|---------|
| **Keepa** | Amazon price/sales rank tracking |
| **GoDaddy** | Domain availability checking |
| **Cloudinary** | Image hosting/CDN |
| **Apollo.io** | Lead enrichment |

---

## 🔗 Key URLs

| Service | URL |
|---------|-----|
| N8N | https://n8n.srv1175204.hstgr.cloud |
| Cal.com | https://cal.srv1175204.hstgr.cloud |
| Webtop | https://webtop.srv1175204.hstgr.cloud |
| Code Server | https://code.srv1175204.hstgr.cloud |
| Botpress | https://botpress.srv1175204.hstgr.cloud |
