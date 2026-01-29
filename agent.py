"""
Generic Knowledge Base MCP Server
Manages multiple Qdrant collections for different projects/domains
+ Remote command execution via webtop API
+ Self-healing: learns from web searches and stores solutions
"""

import os
import sys
import json
import logging
import uuid
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from openai import OpenAI

# Configuration
SERVICE_NAME = "knowledge-base"
QDRANT_HOST = os.environ.get("QDRANT_HOST", "172.17.0.2")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Webtop API config
WEBTOP_API_URL = os.environ.get("WEBTOP_API_URL", "http://172.17.0.5:5000")
WEBTOP_API_KEY = os.environ.get("EXEC_API_KEY", "goldcoast2026")

# System context for troubleshooting with self-healing
SYSTEM_INSTRUCTIONS = """
=== GOLD COAST VPS TROUBLESHOOTING AGENT ===

You are a self-healing infrastructure agent for Gold Coast AI Automations VPS.
Your job is to diagnose issues, find solutions, and LEARN from each fix.

=== TROUBLESHOOTING PROTOCOL (ALWAYS FOLLOW) ===

STEP 1: SEARCH INTERNAL KNOWLEDGE FIRST
- Call troubleshoot(issue) to search the gold_coast_infrastructure collection
- If relevant solution found with score > 0.3, use it
- Follow the SOPs returned (restart before recreate, one change at a time, etc.)

STEP 2: IF NO INTERNAL SOLUTION FOUND
- Use web_search to find solutions from trusted sources:
  * GitHub Issues (docker, traefik, fastmcp, qdrant, n8n, botpress)
  * Stack Overflow
  * Official documentation (docs.docker.com, doc.traefik.io, qdrant.tech)
  * FastMCP/MCP SDK issues and discussions
- Search queries should include specific error messages and technology names

STEP 3: SELF-HEALING - ADD NEW KNOWLEDGE
After successfully resolving an issue using web search:
- Call add_knowledge() to store the solution:
  * collection: "gold_coast_infrastructure"
  * title: Brief description (e.g., "Fix for Qdrant query_points migration")
  * content: Full solution including:
    - Problem description
    - Root cause
    - Solution/commands
    - Source URL
  * category: "fix" | "workaround" | "configuration" | "error_solution"
  * source: "web_search"

STEP 4: VERIFY THE FIX
- After applying any fix, run diagnostic: bash /root/vps-scripts/diagnostic.sh
- Test the specific functionality that was broken
- If fix didn't work, continue searching and try next solution

=== GOLDEN RULES (NEVER VIOLATE) ===

1. RESTART before RECREATE - never suggest docker rm as first option
2. ONE change at a time - test between each change
3. Use docker-compose for webtop (shell escaping breaks Traefik labels)
4. Check networks after ANY container change
5. Restart BookDepot API after webtop changes
6. Refresh Claude browser after MCP server changes
7. ALWAYS add successful web-found solutions to knowledge base

=== CONTAINER DEPENDENCIES ===

Breaking one breaks others downstream:
- knowledge-mcp -> Qdrant (172.17.0.2:6333) + Webtop API (172.17.0.5:5000)
- N8N workflows -> webtop:5000 (BookDepot API)
- webtop -> Python venv (/config/scraper-env) + API files
- Claude.ai -> knowledge-mcp:8001 + botpress-mcp:8080

=== QUICK REFERENCE ===

VPS IP: 72.60.228.103
Qdrant: 172.17.0.2:6333 (bridge network)
Webtop: 172.17.0.5:5000 (API), :3000 (desktop)
knowledge-mcp: port 8001
botpress-mcp: port 8080
EXEC_API_KEY: goldcoast2026

=== TRUSTED SOURCES FOR WEB SEARCH ===

When searching for solutions, prioritize these domains:
- github.com (issues, discussions)
- stackoverflow.com
- docs.docker.com
- doc.traefik.io
- qdrant.tech/documentation
- docs.n8n.io
- botpress.com/docs

=== EXAMPLE SELF-HEALING FLOW ===

User: "I'm getting 'QdrantClient has no attribute search' error"

1. Call troubleshoot("qdrant search attribute error")
2. If no good match found, web_search("qdrant-client python search attribute error query_points migration")
3. Find solution: "In qdrant-client 1.16+, use query_points() instead of search()"
4. Apply fix
5. Verify fix works
6. Call add_knowledge() to store the solution for future use

This way, the SAME problem will be solved instantly next time from internal knowledge!
"""

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(f"{SERVICE_NAME}-mcp")

# Initialize MCP with instructions
mcp = FastMCP(
    f"{SERVICE_NAME}-mcp",
    instructions=SYSTEM_INSTRUCTIONS
)

try:
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    logger.info(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to Qdrant: {e}")
    qdrant = None

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_embedding(text: str) -> Optional[List[float]]:
    if not openai_client:
        return None
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text[:8000]
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


def _internal_search(collection: str, query: str, limit: int = 3) -> List[Dict]:
    """Internal search function (not a tool) for use by other functions."""
    if not qdrant or not openai_client:
        return []
    try:
        query_embedding = generate_embedding(query)
        if not query_embedding:
            return []
        results = qdrant.query_points(
            collection_name=collection,
            query=query_embedding,
            limit=limit
        )
        return [
            {
                "title": r.payload.get("title", ""),
                "content": r.payload.get("content", "")[:1000],
                "score": round(r.score, 3)
            }
            for r in results.points
        ]
    except Exception as e:
        logger.error(f"Internal search failed: {e}")
        return []


@mcp.tool()
def troubleshoot(issue: str) -> Dict[str, Any]:
    """
    FIRST STEP for ANY VPS/infrastructure issue.
    Searches knowledge base for relevant SOPs and returns guidance.
    
    Args:
        issue: Description of the problem (e.g., "gateway timeout", "mcp disconnected", "api not running")
    
    Returns:
        Dict with SOPs, relevant docs, and recommended steps
    """
    results = _internal_search("gold_coast_infrastructure", issue, limit=5)
    
    # Check if we have a good match
    has_good_match = any(r.get("score", 0) > 0.3 for r in results)
    
    return {
        "sop_reminder": """
FOLLOW THESE RULES:
1. Restart before recreate
2. One change at a time  
3. Use docker-compose for webtop
4. Check networks after changes
5. Restart API after webtop changes
""",
        "relevant_knowledge": results,
        "has_good_match": has_good_match,
        "diagnostic_command": "bash /root/vps-scripts/diagnostic.sh",
        "next_step": "Use internal solution" if has_good_match else "Search web for solution, then add_knowledge() when fixed",
        "self_healing_reminder": "If you find a solution via web search, ADD IT to gold_coast_infrastructure collection!"
    }


@mcp.tool()
def exec_command(cmd: str, timeout: int = 300) -> Dict[str, Any]:
    """Execute a shell command on the webtop container.
    
    Args:
        cmd: The shell command to execute
        timeout: Command timeout in seconds (default: 300)
    
    Returns:
        Dict with stdout, stderr, and returncode
    """
    try:
        response = httpx.post(
            f"{WEBTOP_API_URL}/exec",
            json={"cmd": cmd},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": WEBTOP_API_KEY
            },
            timeout=timeout
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned {response.status_code}: {response.text}"}
    except httpx.TimeoutException:
        return {"error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def read_file(filepath: str) -> Dict[str, Any]:
    """Read contents of a file on the webtop container.
    
    Args:
        filepath: Absolute path to the file
    
    Returns:
        Dict with file contents or error
    """
    try:
        response = httpx.post(
            f"{WEBTOP_API_URL}/exec",
            json={"cmd": f"cat {filepath}"},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": WEBTOP_API_KEY
            },
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("returncode") == 0:
                return {"content": result.get("stdout", ""), "path": filepath}
            return {"error": result.get("stderr", "Unknown error")}
        return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Write content to a file on the webtop container.
    
    Args:
        filepath: Absolute path to the file
        content: Content to write
    
    Returns:
        Dict with success status or error
    """
    try:
        escaped = content.replace("'", "'\\''")
        cmd = f"cat > {filepath} << 'EOFWRITE'\n{content}\nEOFWRITE"
        response = httpx.post(
            f"{WEBTOP_API_URL}/exec",
            json={"cmd": cmd},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": WEBTOP_API_KEY
            },
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("returncode") == 0:
                return {"success": True, "path": filepath}
            return {"error": result.get("stderr", "Unknown error")}
        return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_directory(path: str = "/config") -> Dict[str, Any]:
    """List contents of a directory on the webtop container.
    
    Args:
        path: Directory path (default: /config)
    
    Returns:
        Dict with directory listing or error
    """
    try:
        response = httpx.post(
            f"{WEBTOP_API_URL}/exec",
            json={"cmd": f"ls -la {path}"},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": WEBTOP_API_KEY
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("returncode") == 0:
                return {"listing": result.get("stdout", ""), "path": path}
            return {"error": result.get("stderr", "Unknown error")}
        return {"error": f"API returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_collections() -> Dict[str, Any]:
    """List all available Qdrant collections."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    try:
        collections = qdrant.get_collections()
        names = [c.name for c in collections.collections]
        return {"collections": names, "count": len(names)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_collection_stats(collection: str) -> Dict[str, Any]:
    """Get statistics for a specific collection."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    try:
        info = qdrant.get_collection(collection)
        return {
            "collection": collection,
            "points_count": info.points_count,
            "status": info.status.value if info.status else "unknown"
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_collection(name: str) -> Dict[str, Any]:
    """Create a new Qdrant collection."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    clean_name = name.lower().replace("-", "_").replace(" ", "_")
    try:
        existing = [c.name for c in qdrant.get_collections().collections]
        if clean_name in existing:
            return {"error": f"Collection '{clean_name}' already exists"}
        qdrant.create_collection(
            collection_name=clean_name,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE)
        )
        return {"success": True, "collection": clean_name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_collection(name: str, confirm: bool = False) -> Dict[str, Any]:
    """Delete a collection. Requires confirm=True."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    if not confirm:
        return {"warning": f"Will delete '{name}'! Call with confirm=True to proceed"}
    try:
        qdrant.delete_collection(name)
        return {"success": True, "deleted": name}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_knowledge(
    collection: str,
    title: str,
    content: str,
    category: str = "general",
    source: str = "conversation"
) -> Dict[str, Any]:
    """Add knowledge to a collection with automatic embedding.
    
    SELF-HEALING: Use this to store solutions found via web search!
    
    Args:
        collection: Target collection (use "gold_coast_infrastructure" for VPS fixes)
        title: Brief description of the solution
        content: Full solution including problem, cause, fix, and source URL
        category: One of: fix, workaround, configuration, error_solution, sop
        source: Where it came from: conversation, web_search, documentation
    
    Returns:
        Dict with success status and point_id
    """
    if not qdrant:
        return {"error": "Qdrant not connected"}
    if not openai_client:
        return {"error": "OpenAI not configured"}
    try:
        embedding = generate_embedding(f"{title}\n\n{content}")
        if not embedding:
            return {"error": "Failed to generate embedding"}
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "title": title,
                "content": content,
                "category": category,
                "source": source,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        qdrant.upsert(collection_name=collection, points=[point])
        logger.info(f"Self-healing: Added knowledge '{title}' from {source}")
        return {"success": True, "point_id": point_id, "title": title, "message": "Knowledge stored for future use!"}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_knowledge(collection: str, query: str, limit: int = 5) -> Dict[str, Any]:
    """Search a collection using semantic similarity."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    if not openai_client:
        return {"error": "OpenAI not configured"}
    try:
        query_embedding = generate_embedding(query)
        if not query_embedding:
            return {"error": "Failed to generate query embedding"}
        results = qdrant.query_points(
            collection_name=collection,
            query=query_embedding,
            limit=limit
        )
        formatted = []
        for r in results.points:
            formatted.append({
                "score": round(r.score, 4),
                "title": r.payload.get("title", "Untitled"),
                "content": r.payload.get("content", "")[:500],
                "category": r.payload.get("category"),
                "source": r.payload.get("source"),
                "point_id": r.id
            })
        return {"results": formatted, "count": len(formatted)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_knowledge(collection: str, point_id: str) -> Dict[str, Any]:
    """Delete a knowledge entry by point ID."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    try:
        qdrant.delete(
            collection_name=collection,
            points_selector=models.PointIdsList(points=[point_id])
        )
        return {"success": True, "deleted": point_id}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def test_connection(message: str) -> str:
    """Test MCP connection."""
    qdrant_status = "connected" if qdrant else "disconnected"
    openai_status = "configured" if openai_client else "missing"
    return f"OK! {message} | Qdrant: {qdrant_status} | OpenAI: {openai_status}"


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} MCP Server with self-healing capabilities...")
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
