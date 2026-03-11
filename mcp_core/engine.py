"""
mcp_core/engine.py – All MCP boilerplate. You never need to touch this file.

Usage (in mcp_server.py):

    from mcp_core.engine import create_app

    TOOLS = {
        "say_hello": {
            "fn":          say_hello,
            "description": "Says hello",
            "params":      {"name": {"type": "string"}},
            "required":    ["name"],
        },
    }
    app = create_app(TOOLS)

Each tool function receives a dict of args and must return:
    {"text": "plain text for ChatGPT", "html": "<h1>Hello</h1>"}
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from constants import MIME_TYPE, WIDGET_URI


def _make_mcp() -> FastMCP:
    return FastMCP(
        name="testbook-chatgpt-app",
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


def _widget_shell() -> str:
    """Base HTML shell sent when ChatGPT first loads the widget."""
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <style>
    *{box-sizing:border-box}
    body{margin:0;font-family:system-ui,sans-serif;background:#0b1020;color:#edf2ff;padding:16px}
  </style>
</head>
<body>
  <div id="app"><p style="color:#a9b4d0">Ready.</p></div>
  <script>
    let rpcId=0;const pending=new Map();
    function rpcNotify(m,p){window.parent.postMessage({jsonrpc:"2.0",method:m,params:p},"*")}
    function rpcRequest(m,p){return new Promise((res,rej)=>{const id=++rpcId;pending.set(id,{resolve:res,reject:rej});window.parent.postMessage({jsonrpc:"2.0",id,method:m,params:p},"*")})}
    window.addEventListener("message",e=>{if(e.source!==window.parent)return;const m=e.data;if(!m||m.jsonrpc!=="2.0")return;if(typeof m.id==="number"){const w=pending.get(m.id);if(!w)return;pending.delete(m.id);if(m.error)w.reject(m.error);else w.resolve(m.result);return}if(m.method==="ui/notifications/tool-result"){const r=m.params||{};document.getElementById("app").innerHTML=r.structuredContent?.html||""}},{passive:true});
    (async()=>{await rpcRequest("ui/initialize",{appInfo:{name:"testbook-widget",version:"0.1.0"},appCapabilities:{},protocolVersion:"2026-01-26"});rpcNotify("ui/notifications/initialized",{})})().catch(console.error);
    async function callTool(name,args){const r=await rpcRequest("tools/call",{name,arguments:args||{}});document.getElementById("app").innerHTML=r.structuredContent?.html||""}
  </script>
</body>
</html>"""


_META = {
    "openai/outputTemplate": WIDGET_URI,
    "openai/widgetAccessible": True,
    "ui": {"resourceUri": WIDGET_URI},
}

_WIDGET_META = {
    "openai/outputTemplate": WIDGET_URI,
    "openai/widgetAccessible": True,
    "openai/widgetPrefersBorder": True,
    "ui": {"prefersBorder": True},
}


def create_app(tools: Dict[str, Dict[str, Any]]):
    """
    Wire up a dict of tools into a running ASGI MCP app.

    tools = {
        "name": {
            "fn":          callable(args_dict) -> {"text": str, "html": str},
            "description": str,
            "params":      {json schema properties},
            "required":    [list of required param names],
        }
    }
    """
    mcp = _make_mcp()

    @mcp._mcp_server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(
                name=name,
                title=name,
                description=spec["description"],
                inputSchema={
                    "type": "object",
                    "properties": deepcopy(spec.get("params", {})),
                    "required": spec.get("required", []),
                    "additionalProperties": False,
                },
                _meta=_META,
                annotations={"readOnlyHint": True, "destructiveHint": False},
            )
            for name, spec in tools.items()
        ]

    @mcp._mcp_server.list_resources()
    async def list_resources() -> List[types.Resource]:
        return [types.Resource(
            name="Widget", title="Widget", uri=WIDGET_URI,
            description="Inline UI", mimeType=MIME_TYPE, _meta=_WIDGET_META,
        )]

    @mcp._mcp_server.list_resource_templates()
    async def list_resource_templates() -> List[types.ResourceTemplate]:
        return [types.ResourceTemplate(
            name="Widget", title="Widget", uriTemplate=WIDGET_URI,
            description="Inline UI", mimeType=MIME_TYPE, _meta=_WIDGET_META,
        )]

    async def handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
        return types.ServerResult(types.ReadResourceResult(contents=[
            types.TextResourceContents(
                uri=WIDGET_URI, mimeType=MIME_TYPE,
                text=_widget_shell(), _meta=_WIDGET_META,
            )
        ]))

    async def handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
        name = req.params.name
        args = req.params.arguments or {}
        spec = tools.get(name)

        if not spec:
            return types.ServerResult(types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            ))
        try:
            result = spec["fn"](args)
            return types.ServerResult(types.CallToolResult(
                content=[types.TextContent(type="text", text=result.get("text", ""))],
                structuredContent={"html": result.get("html", "")},
                _meta=_META,
            ))
        except Exception as exc:
            return types.ServerResult(types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: {exc}")],
                isError=True,
            ))

    mcp._mcp_server.request_handlers[types.ReadResourceRequest] = handle_read_resource
    mcp._mcp_server.request_handlers[types.CallToolRequest] = handle_call_tool

    app = mcp.streamable_http_app()
    try:
        from starlette.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    except Exception:
        pass

    return app

