import hashlib
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

NORMALIZED_EMAIL = "24f3000130@ds.study.iitm.ac.in".strip().lower()

@app.get("/")
async def root():
    return {"status": "MCP server is live"}

@app.post("/")
@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
        )

    is_batch = isinstance(body, list)
    requests = body if is_batch else [body]
    responses = []

    for req in requests:
        resp = await process_jsonrpc(req, request)
        if resp is not None:
            responses.append(resp)

    if is_batch:
        return JSONResponse(content=responses)
    elif responses:
        return JSONResponse(content=responses[0])
    else:
        return JSONResponse(status_code=200, content={})

async def process_jsonrpc(req: Dict[str, Any], request: Request) -> Dict[str, Any] | None:
    method = req.get("method")
    req_id = req.get("id")

    # 1. MCP Initialization Handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "exam-mcp-server",
                    "version": "1.0.0"
                }
            }
        }

    # 2. Initialized Notification
    elif method == "notifications/initialized":
        return None

    # 3. List Tools
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "solve_challenge",
                        "description": "Solves dynamic header-based verification challenges.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }
        }

    # 4. Tool Call
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")

        if tool_name != "solve_challenge":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

        challenge = request.headers.get("x-exam-challenge", "").strip()
        payload = f"{challenge}:{NORMALIZED_EMAIL}".encode("utf-8")
        full_hash = hashlib.sha256(payload).hexdigest()
        result_text = full_hash[:16].lower()

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
        }

    # Unknown JSON-RPC method fallback
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }
    return None

