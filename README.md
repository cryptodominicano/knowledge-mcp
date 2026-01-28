# Knowledge MCP Server

FastMCP server providing tools for:
- Qdrant vector database operations
- Webtop/BookDepot API integration
- N8N workflow management
- Shell command execution

## Tools

- `exec_command` - Execute shell commands on webtop
- `list_collections` - List Qdrant collections
- `search_knowledge` - Semantic search in Qdrant
- `add_knowledge` - Add to knowledge base
- N8N workflow tools (list, create, update, execute)

## Environment Variables

- `OPENAI_API_KEY` - For embeddings
- `QDRANT_HOST` - Qdrant container IP
- `WEBTOP_API_URL` - BookDepot API URL
- `WEBTOP_API_KEY` - API authentication
- `N8N_API_KEY` - N8N API token
- `N8N_BASE_URL` - N8N internal URL
