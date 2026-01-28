"""
Generic Knowledge Base MCP Server
Manages multiple Qdrant collections for different projects/domains
+ Remote command execution via webtop API
+ N8N workflow automation
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
WEBTOP_API_URL = os.environ.get("WEBTOP_API_URL", "http://webtop:5000")
WEBTOP_API_KEY = os.environ.get("WEBTOP_API_KEY", "goldcoast2026")

# N8N API config
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://root-n8n-1:5678")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(f"{SERVICE_NAME}-mcp")

# Initialize
mcp = FastMCP(f"{SERVICE_NAME}-mcp")

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


def n8n_request(method: str, endpoint: str, data: dict = None) -> Dict[str, Any]:
    """Make authenticated request to N8N API."""
    if not N8N_API_KEY:
        return {"error": "N8N_API_KEY not configured"}
    
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }
    url = f"{N8N_BASE_URL}/api/v1{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = httpx.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = httpx.post(url, headers=headers, json=data or {}, timeout=60)
        elif method.upper() == "PUT":
            response = httpx.put(url, headers=headers, json=data or {}, timeout=30)
        elif method.upper() == "PATCH":
            response = httpx.patch(url, headers=headers, json=data or {}, timeout=30)
        elif method.upper() == "DELETE":
            response = httpx.delete(url, headers=headers, timeout=30)
        else:
            return {"error": f"Unknown method: {method}"}
        
        if response.status_code >= 200 and response.status_code < 300:
            return response.json() if response.text else {"success": True}
        else:
            return {"error": f"HTTP {response.status_code}", "detail": response.text[:500]}
    except Exception as e:
        return {"error": str(e)}


# =====================
# N8N WORKFLOW TOOLS
# =====================

@mcp.tool()
def n8n_list_workflows(limit: int = 50, active_only: bool = False) -> Dict[str, Any]:
    """List all N8N workflows.
    
    Args:
        limit: Maximum workflows to return (default: 50)
        active_only: Only show active workflows
    
    Returns:
        List of workflows with id, name, active status
    """
    result = n8n_request("GET", f"/workflows?limit={limit}")
    if "error" in result:
        return result
    
    workflows = result.get("data", [])
    if active_only:
        workflows = [w for w in workflows if w.get("active")]
    
    formatted = []
    for w in workflows:
        formatted.append({
            "id": w.get("id"),
            "name": w.get("name"),
            "active": w.get("active"),
            "updatedAt": w.get("updatedAt")
        })
    return {"workflows": formatted, "count": len(formatted)}


@mcp.tool()
def n8n_get_workflow(workflow_id: str) -> Dict[str, Any]:
    """Get full workflow details including all nodes and connections.
    
    Args:
        workflow_id: The workflow ID
    
    Returns:
        Complete workflow JSON with nodes, connections, settings
    """
    return n8n_request("GET", f"/workflows/{workflow_id}")


@mcp.tool()
def n8n_create_workflow(name: str, nodes: List[dict], connections: dict, active: bool = False) -> Dict[str, Any]:
    """Create a new N8N workflow.
    
    Args:
        name: Workflow name
        nodes: List of node definitions
        connections: Node connections object
        active: Whether to activate immediately
    
    Returns:
        Created workflow details
    """
    data = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": active,
        "settings": {"executionOrder": "v1"}
    }
    return n8n_request("POST", "/workflows", data)


@mcp.tool()
def n8n_update_workflow(workflow_id: str, updates: dict) -> Dict[str, Any]:
    """Update an existing workflow.
    
    Args:
        workflow_id: The workflow ID
        updates: Dictionary of fields to update (name, nodes, connections, active, settings)
    
    Returns:
        Updated workflow details
    """
    return n8n_request("PUT", f"/workflows/{workflow_id}", updates)


@mcp.tool()
def n8n_activate_workflow(workflow_id: str, active: bool = True) -> Dict[str, Any]:
    """Activate or deactivate a workflow.
    
    Args:
        workflow_id: The workflow ID
        active: True to activate, False to deactivate
    
    Returns:
        Updated workflow status
    """
    if active:
        return n8n_request("POST", f"/workflows/{workflow_id}/activate")
    else:
        return n8n_request("POST", f"/workflows/{workflow_id}/deactivate")


@mcp.tool()
def n8n_delete_workflow(workflow_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Delete a workflow. Requires confirm=True.
    
    Args:
        workflow_id: The workflow ID
        confirm: Must be True to actually delete
    
    Returns:
        Deletion result
    """
    if not confirm:
        return {"warning": f"Will DELETE workflow {workflow_id}! Set confirm=True to proceed"}
    return n8n_request("DELETE", f"/workflows/{workflow_id}")


@mcp.tool()
def n8n_execute_workflow(workflow_id: str, data: dict = None) -> Dict[str, Any]:
    """Manually execute/trigger a workflow.
    
    Args:
        workflow_id: The workflow ID
        data: Optional input data to pass to the workflow
    
    Returns:
        Execution result
    """
    return n8n_request("POST", f"/workflows/{workflow_id}/run", data or {})


@mcp.tool()
def n8n_list_executions(workflow_id: str = None, limit: int = 20, status: str = None) -> Dict[str, Any]:
    """List workflow executions (run history).
    
    Args:
        workflow_id: Filter by specific workflow (optional)
        limit: Maximum results (default: 20)
        status: Filter by status: success, error, waiting (optional)
    
    Returns:
        List of executions with status and timing
    """
    params = f"?limit={limit}"
    if workflow_id:
        params += f"&workflowId={workflow_id}"
    if status:
        params += f"&status={status}"
    
    result = n8n_request("GET", f"/executions{params}")
    if "error" in result:
        return result
    
    executions = result.get("data", [])
    formatted = []
    for e in executions:
        formatted.append({
            "id": e.get("id"),
            "workflowId": e.get("workflowId"),
            "status": e.get("status"),
            "startedAt": e.get("startedAt"),
            "stoppedAt": e.get("stoppedAt"),
            "finished": e.get("finished")
        })
    return {"executions": formatted, "count": len(formatted)}


@mcp.tool()
def n8n_get_execution(execution_id: str) -> Dict[str, Any]:
    """Get detailed execution info including error messages.
    
    Args:
        execution_id: The execution ID
    
    Returns:
        Full execution details including node results and errors
    """
    return n8n_request("GET", f"/executions/{execution_id}")


@mcp.tool()
def n8n_test_connection() -> Dict[str, Any]:
    """Test N8N API connection."""
    if not N8N_API_KEY:
        return {"status": "error", "message": "N8N_API_KEY not configured"}
    
    result = n8n_request("GET", "/workflows?limit=1")
    if "error" in result:
        return {"status": "error", "message": result.get("error")}
    return {"status": "connected", "base_url": N8N_BASE_URL}


# =====================
# WEBTOP EXEC TOOLS
# =====================

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
    result = exec_command(f"cat {filepath}")
    if result.get("returncode") == 0:
        return {"content": result.get("stdout", ""), "filepath": filepath}
    return {"error": result.get("stderr") or result.get("error", "Unknown error")}


@mcp.tool()
def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Write content to a file on the webtop container.
    
    Args:
        filepath: Absolute path to the file
        content: Content to write
    
    Returns:
        Dict with success status or error
    """
    # Escape content for shell
    escaped = content.replace("'", "'\\''")
    result = exec_command(f"cat > {filepath} << 'EOFMARKER'\n{content}\nEOFMARKER")
    if result.get("returncode") == 0:
        return {"success": True, "filepath": filepath}
    return {"error": result.get("stderr") or result.get("error", "Unknown error")}


@mcp.tool()
def list_directory(path: str = "/config") -> Dict[str, Any]:
    """List contents of a directory on the webtop container.
    
    Args:
        path: Directory path (default: /config)
    
    Returns:
        Dict with directory listing or error
    """
    result = exec_command(f"ls -la {path}")
    if result.get("returncode") == 0:
        return {"listing": result.get("stdout", ""), "path": path}
    return {"error": result.get("stderr") or result.get("error", "Unknown error")}


# =====================
# QDRANT KNOWLEDGE TOOLS
# =====================

@mcp.tool()
def list_collections() -> Dict[str, Any]:
    """List all available Qdrant collections."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    try:
        collections = qdrant.get_collections().collections
        return {"collections": [c.name for c in collections]}
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
            "name": collection,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_collection(name: str) -> Dict[str, Any]:
    """Create a new Qdrant collection."""
    if not qdrant:
        return {"error": "Qdrant not connected"}
    try:
        qdrant.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE)
        )
        return {"success": True, "collection": name}
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
    """Add knowledge to a collection with automatic embedding."""
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
        return {"success": True, "point_id": point_id, "title": title}
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
        results = qdrant.search(
            collection_name=collection,
            query_vector=query_embedding,
            limit=limit
        )
        formatted = []
        for r in results:
            formatted.append({
                "score": round(r.score, 4),
                "title": r.payload.get("title", "Untitled"),
                "content": r.payload.get("content", "")[:500],
                "category": r.payload.get("category"),
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
    n8n_status = "configured" if N8N_API_KEY else "missing"
    return f"OK! {message} | Qdrant: {qdrant_status} | OpenAI: {openai_status} | N8N: {n8n_status}"


if __name__ == "__main__":
    logger.info(f"Starting {SERVICE_NAME} MCP Server...")
    logger.info(f"N8N configured: {bool(N8N_API_KEY)}")
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
