# OpenAI Store - MCP Server Architecture

## 📋 Overview

This is a **Model Context Protocol (MCP) Server** that integrates with ChatGPT to provide custom tools with rich interactive UI widgets. The application exposes tools that ChatGPT can call, and each tool returns both plain text and HTML rendering.

---

## 🏗️ System Architecture

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         ChatGPT Client                          │
│                    (OpenAI ChatGPT Interface)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/MCP Protocol
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                  MCP Server (FastMCP)                           │
│              uvicorn @ http://127.0.0.1:8000                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │           mcp_core/engine.py (Engine/Core)                 ││
│  │  - Initializes FastMCP server                              ││
│  │  - Routes tool calls                                       ││
│  │  - Manages tool registry                                   ││
│  │  - Handles resource serving (HTML widget shell)            ││
│  └─────────────────────────────────────────────────────────────┘│
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    ↓                 ↓                          │
│  ┌──────────────────────┐  ┌──────────────────────┐           │
│  │  Tool: say_hello     │  │  Tool: say_goodbye   │           │
│  │  (tools/say_hello.py)│  │(tools/say_goodbye.py)│           │
│  │                      │  │                      │           │
│  │ • Accepts: name      │  │ • Accepts: name      │           │
│  │ • Returns:           │  │ • Returns:           │           │
│  │   - text: greeting   │  │   - text: farewell   │           │
│  │   - html: card UI    │  │   - html: card UI    │           │
│  └──────────────────────┘  └──────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Directory Structure & File Purposes

```
OpenAIStore/
├── mcp_server.py              ⭐ MAIN ENTRY POINT
│   └── Purpose: Register and start the MCP server
│       - Imports tools from tools/
│       - Defines TOOLS dict with tool metadata
│       - Creates and runs the FastMCP app via create_app()
│
├── mcp_core/
│   ├── __init__.py
│   └── engine.py              🔧 CORE ENGINE (Don't touch!)
│       └── Purpose: MCP server boilerplate
│           - create_app(): Initializes FastMCP server
│           - Handles tool registration
│           - Routes tool calls from ChatGPT
│           - Manages HTML widget rendering
│           - Defines request/response handlers
│
├── tools/                      🛠️ TOOL IMPLEMENTATIONS
│   ├── __init__.py
│   ├── say_hello.py
│   │   └── say_hello(args) → {"text": str, "html": str}
│   └── say_goodbye.py
│       └── say_goodbye(args) → {"text": str, "html": str}
│
├── constants.py               ⚙️ CONFIGURATION
│   └── APP_NAME, PORT, MIME_TYPE, WIDGET_URI
│
├── assets/
│   └── goalDetails.csv        📊 Data files (if used by tools)
│
└── README.md / ARCHITECTURE.md 📖 Documentation
```

---

## 🔄 Execution Flow: Start to End

### Phase 1: Server Startup

```
START (python mcp_server.py)
  │
  ├─ 1. Load constants from constants.py
  │      - APP_NAME = "Testbook ChatGPT App"
  │      - PORT = 8000
  │      - WIDGET_URI = "ui://widget/testbook-app.html"
  │
  ├─ 2. Import tools
  │      - from tools.say_hello import say_hello
  │      - from tools.say_goodbye import say_goodbye
  │
  ├─ 3. Define TOOLS dict (in mcp_server.py)
  │      TOOLS = {
  │          "say_hello": {
  │              "fn": say_hello,
  │              "description": "Say hello to someone...",
  │              "params": {"name": {"type": "string"}},
  │              "required": ["name"]
  │          },
  │          "say_goodbye": { ... }
  │      }
  │
  ├─ 4. Call create_app(TOOLS)
  │      └─ Initializes FastMCP server
  │         └─ Registers all tools from TOOLS dict
  │            └─ Sets up request handlers
  │
  ├─ 5. Start uvicorn server
  │      - Listen on 0.0.0.0:8000
  │      - Server ready for ChatGPT connections
  │
  └─ ✅ Server Running
```

### Phase 2: Initial ChatGPT Connection

```
ChatGPT Connects to MCP Server
  │
  ├─ 1. ChatGPT requests available resources
  │      GET /resources or MCP protocol
  │
  ├─ 2. engine.py → list_resources()
  │      └─ Returns: Widget resource
  │         - name: "Widget"
  │         - uri: "ui://widget/testbook-app.html"
  │         - mimeType: "text/html+skybridge"
  │
  ├─ 3. engine.py → handle_read_resource()
  │      └─ Returns: _widget_shell() HTML
  │         └─ Embedded JavaScript for tool calls
  │
  ├─ 4. ChatGPT requests available tools
  │      │
  │      └─ engine.py → list_tools()
  │         └─ Returns list of Tool objects:
  │            [
  │              Tool(name="say_hello", description="...", params={...}),
  │              Tool(name="say_goodbye", description="...", params={...})
  │            ]
  │
  └─ ✅ ChatGPT UI loaded with tools available
```

### Phase 3: User Calls a Tool

```
User in ChatGPT: "Say hello to Alice"
  │
  ├─ 1. ChatGPT decides to call: say_hello(name="Alice")
  │
  ├─ 2. ChatGPT sends MCP request to engine.py
  │      CallToolRequest:
  │      {
  │          "name": "say_hello",
  │          "arguments": {"name": "Alice"}
  │      }
  │
  ├─ 3. engine.py → handle_call_tool()
  │      │
  │      ├─ Extract tool name: "say_hello"
  │      ├─ Extract args: {"name": "Alice"}
  │      ├─ Look up tool in TOOLS dict
  │      │
  │      └─ Call: TOOLS["say_hello"]["fn"]({"name": "Alice"})
  │         │
  │         └─ tools/say_hello.py → say_hello(args)
  │            ├─ name = args.get("name", "World")  # "Alice"
  │            ├─ Generate HTML card UI
  │            └─ Return:
  │               {
  │                   "text": "Hello, Alice!",
  │                   "html": "<div>...greeting card...</div>"
  │               }
  │
  ├─ 4. engine.py → CallToolResult
  │      └─ Wrap result in MCP response:
  │         {
  │             "content": [
  │                 TextContent(text: "Hello, Alice!")
  │             ],
  │             "structuredContent": {
  │                 "html": "<div>...greeting card...</div>"
  │             }
  │         }
  │
  ├─ 5. Send response to ChatGPT
  │
  ├─ 6. ChatGPT renders HTML in widget
  │      └─ Shows: greeting card with "Say Goodbye →" button
  │
  └─ ✅ Tool execution complete, result shown to user
```

### Phase 4: User Clicks Interactive Button

```
User clicks "Say Goodbye →" button in HTML widget
  │
  ├─ 1. Embedded JavaScript in widget (from _widget_shell())
  │      callTool("say_goodbye", {"name": "Alice"})
  │
  ├─ 2. Calls: rpcRequest("tools/call", {...})
  │      └─ Sends new MCP CallToolRequest to engine
  │
  ├─ 3. engine.py → handle_call_tool()
  │      └─ Same as Phase 3, but for say_goodbye
  │         └─ tools/say_goodbye.py → say_goodbye(args)
  │            └─ Returns HTML for goodbye card
  │
  ├─ 4. Widget re-renders with new HTML
  │
  └─ ✅ Interactive flow complete
```

---

## 🔌 How Tools Are Registered & Called

### Tool Definition (in mcp_server.py)

```python
TOOLS = {
    "say_hello": {
        "fn": say_hello,                    # Function to call
        "description": "Say hello to someone. Renders a greeting card.",
        "params": {                         # JSON Schema for parameters
            "name": {
                "type": "string",
                "description": "Name to greet"
            }
        },
        "required": ["name"],               # Which params are required
    },
    # ... more tools
}
```

### Tool Execution Pipeline

```
mcp_server.py (TOOLS dict)
    ↓
engine.py:list_tools()
    └─ Converts TOOLS dict → Tool objects
       └─ ChatGPT knows about tools
    ↓
User action in ChatGPT
    ↓
engine.py:handle_call_tool()
    ├─ Extract tool name & arguments
    ├─ Look up in TOOLS dict
    ├─ Call TOOLS[name]["fn"](arguments)
    │   ↓
    │   tools/say_hello.py:say_hello()
    │   tools/say_goodbye.py:say_goodbye()
    │   (or any custom tool you add)
    │   
    │   Must return: {"text": str, "html": str}
    │
    └─ Wrap in CallToolResult → Send to ChatGPT
```

---

## 📝 How to Add a New Tool

**Follow the 4-step process (already documented in mcp_server.py):**

### Step 1: Create tool file in `tools/`

**File:** `tools/my_new_tool.py`
```python
def my_new_tool(args: dict) -> dict:
    param1 = args.get("param1", "default_value")
    param2 = args.get("param2", "default_value")
    
    # Your logic here
    text_result = f"Processed: {param1}, {param2}"
    html_result = f"<div>Result: {text_result}</div>"
    
    return {
        "text": text_result,
        "html": html_result,
    }
```

### Step 2: Import in `mcp_server.py`

```python
from tools.my_new_tool import my_new_tool
```

### Step 3: Register in TOOLS dict

```python
TOOLS = {
    # ... existing tools ...
    "my_new_tool": {
        "fn":          my_new_tool,
        "description": "Description of what your tool does",
        "params": {
            "param1": {"type": "string", "description": "First parameter"},
            "param2": {"type": "string", "description": "Second parameter"},
        },
        "required":    ["param1"],  # Leave empty if all optional
    },
}
```

### Step 4: Done! 

The tool is now:
- ✅ Registered in the MCP server
- ✅ Available to ChatGPT
- ✅ Ready to be called

---

## 🎨 Understanding the Widget & HTML Rendering

### Widget Shell (`_widget_shell()`)

The HTML widget that ChatGPT loads includes:

1. **Styling**: Dark theme with gradients
2. **JavaScript Bridge**: Communication between ChatGPT and tools
3. **Message Listener**: Receives tool results
4. **Tool Caller**: `callTool(name, args)` function to invoke tools

### Tool HTML Response

Each tool returns HTML that gets injected into `<div id="app">`:

```html
<!-- say_hello returns: -->
<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);...">
  <h1>👋 Hello, Alice!</h1>
  <p>Welcome to Testbook ChatGPT App.</p>
  <button onclick='callTool("say_goodbye", {"name":"Alice"})'>
    Say Goodbye →
  </button>
</div>
```

---

## 🚀 Deployment & Configuration

### Environment Variables

Set via `.env` or export:
```bash
PORT=8000  # Default if not set
```

### Start Server

```bash
# Terminal 1: Start the server
python mcp_server.py

# Output:
# Starting Testbook ChatGPT App on http://127.0.0.1:8000
```

### Connect to ChatGPT

1. Open ChatGPT web interface
2. Configure custom GPT or plugin to use: `http://127.0.0.1:8000`
3. ChatGPT will auto-discover tools and resources
4. Start using tools in conversation

---

## 📊 Data Flow Diagram: Tool Call

```
┌──────────────────┐
│   ChatGPT User   │
│ "Say hello to X" │
└────────┬─────────┘
         │
         ↓
┌──────────────────────────────────────┐
│  ChatGPT decides to call "say_hello" │
└────────┬─────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────┐
│  MCP Protocol: CallToolRequest               │
│  {                                           │
│    "name": "say_hello",                      │
│    "arguments": {"name": "X"}                │
│  }                                           │
└────────┬─────────────────────────────────────┘
         │
         ↓ (HTTP POST to :8000)
┌──────────────────────────────────────────────┐
│  engine.py: handle_call_tool()               │
│  1. Parse request                            │
│  2. Look up "say_hello" in TOOLS             │
│  3. Extract arguments {"name": "X"}          │
└────────┬─────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────┐
│  tools/say_hello.py: say_hello(args)         │
│  1. Get name from args: "X"                  │
│  2. Generate greeting text & HTML            │
│  3. Return {text, html}                      │
└────────┬─────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────┐
│  engine.py: Build CallToolResult             │
│  {                                           │
│    "content": [TextContent],                 │
│    "structuredContent": {"html": "..."}      │
│  }                                           │
└────────┬─────────────────────────────────────┘
         │
         ↓ (HTTP Response)
┌──────────────────────────────────────────────┐
│  ChatGPT receives response                   │
│  Renders HTML in widget                      │
│  Shows greeting card to user                 │
└──────────────────────────────────────────────┘
```

---

## 🔐 Key Concepts

| Concept | Purpose | Location |
|---------|---------|----------|
| **MCP Server** | Protocol for AI-tool communication | `engine.py` |
| **FastMCP** | Framework for building MCP servers | `mcp_core/` |
| **Tools Dict** | Registry of available functions | `mcp_server.py` |
| **Tool Function** | Actual logic that gets executed | `tools/*.py` |
| **Widget Shell** | HTML/JS interface for UI | `engine.py:_widget_shell()` |
| **CallToolRequest** | MCP message: "call this tool" | `mcp.types` |
| **CallToolResult** | MCP message: "here's the result" | `mcp.types` |

---

## 🎯 Quick Reference

### To Add a Tool
1. Create `tools/my_tool.py` with `my_tool(args: dict) -> dict`
2. Import in `mcp_server.py`
3. Add entry to `TOOLS` dict
4. Done!

### Tool Function Contract
```python
def my_tool(args: dict) -> dict:
    """
    Args: Dictionary of parameters passed by ChatGPT
    Returns: {"text": "plain text", "html": "<html>..."}
    """
    # Your code here
    return {"text": "result", "html": "<div>result</div>"}
```

### Testing a Tool
```bash
# 1. Start server
python mcp_server.py

# 2. In another terminal, test with curl
curl http://127.0.0.1:8000/tool/say_hello?name=Alice
```

---

## 📚 File Dependencies

```
mcp_server.py ← ENTRY POINT
  ├─ Imports: tools.say_hello, tools.say_goodbye
  ├─ Imports: mcp_core.engine.create_app
  ├─ Imports: constants.APP_NAME, PORT
  │
  └─ Creates: TOOLS dict
      └─ Passes to: engine.create_app(TOOLS)
          ├─ Uses: mcp.types for MCP protocol
          ├─ Uses: constants.MIME_TYPE, WIDGET_URI
          ├─ Defines: list_tools(), handle_call_tool()
          │   └─ Calls: tools/say_hello.say_hello()
          │   └─ Calls: tools/say_goodbye.say_goodbye()
          │
          └─ Returns: FastMCP ASGI app
              └─ Served by: uvicorn
```

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Tool not showing in ChatGPT | Not added to TOOLS dict | Ensure tool is imported and in TOOLS dict |
| Tool call returns error | Exception in tool function | Add try-catch in your tool, check args |
| HTML not rendering | Invalid HTML returned | Check returned HTML structure, no unclosed tags |
| Server won't start | Port already in use | Change PORT in constants.py or environment |
| Widget not loading | WIDGET_URI mismatch | Check WIDGET_URI in constants.py matches ChatGPT config |

---

## 📌 Summary

This MCP Server:
1. **Starts** in `mcp_server.py` with TOOLS dict
2. **Initializes** via `engine.py:create_app()`
3. **Registers** tools with FastMCP
4. **Listens** on port 8000 for ChatGPT
5. **Routes** tool calls to functions in `tools/`
6. **Returns** text + HTML responses
7. **Renders** results in ChatGPT widget

Add new tools by: Create → Import → Register → Done!

