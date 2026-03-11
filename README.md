# OpenAI Store - Testbook ChatGPT Integration

An MCP (Model Context Protocol) server that integrates with ChatGPT to provide custom tools with rich interactive UI widgets. This application allows ChatGPT to call custom tools and render beautiful HTML responses with interactive buttons.

## 🎯 Project Overview

This is a Python-based MCP server built with [FastMCP](https://github.com/jqlang/fastmcp) that:

- ✅ Exposes custom tools to ChatGPT
- ✅ Renders rich HTML UI widgets for each tool
- ✅ Supports interactive buttons and tool chaining
- ✅ Easy to extend with new tools
- ✅ Built for the Testbook ChatGPT integration

## 📚 Documentation

For detailed architecture, flow diagrams, and implementation guide, see:
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete system overview, execution flow, and design patterns

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip
- GitHub account (for deploying)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/OpenAIStore.git
   cd OpenAIStore
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server

```bash
python mcp_server.py
```

The server will start on `http://127.0.0.1:8000`

### Connecting to ChatGPT

1. Open your ChatGPT interface
2. Configure a custom tool/plugin to use: `http://127.0.0.1:8000`
3. ChatGPT will auto-discover the available tools
4. Start using the tools in your conversation

## 📁 Project Structure

```
OpenAIStore/
├── mcp_server.py              # Main entry point - tool registration
├── constants.py               # Configuration and constants
├── mcp_core/
│   ├── __init__.py
│   └── engine.py             # MCP server boilerplate (do not modify)
├── tools/
│   ├── __init__.py
│   ├── say_hello.py          # Example tool: greet user
│   └── say_goodbye.py        # Example tool: farewell
├── assets/
│   └── goalDetails.csv       # Sample data file
├── ARCHITECTURE.md           # Detailed system documentation
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```

## 🛠️ Available Tools

### say_hello
Greets a user with a personalized greeting card.

**Parameters:**
- `name` (string, required): Name to greet

**Returns:**
- Text: Greeting message
- HTML: Interactive greeting card with "Say Goodbye" button

### say_goodbye
Bids farewell to a user with a goodbye card.

**Parameters:**
- `name` (string, required): Name to say goodbye to

**Returns:**
- Text: Farewell message
- HTML: Interactive goodbye card with "Say Hello Again" button

## 📝 Creating New Tools

Follow these 4 simple steps:

### Step 1: Create Tool File

Create `tools/my_tool.py`:
```python
def my_tool(args: dict) -> dict:
    """
    Tool function that ChatGPT can call.
    
    Args:
        args: Dictionary of parameters from ChatGPT
        
    Returns:
        Dictionary with 'text' and 'html' keys
    """
    param1 = args.get("param1", "default")
    param2 = args.get("param2", "default")
    
    text_result = f"Result: {param1}, {param2}"
    html_result = f"""
    <div style="padding:20px; background:#f0f0f0; border-radius:8px;">
        <h2>{text_result}</h2>
        <p>Your custom tool output here</p>
    </div>
    """
    
    return {
        "text": text_result,
        "html": html_result,
    }
```

### Step 2: Import in mcp_server.py

```python
from tools.my_tool import my_tool
```

### Step 3: Register in TOOLS Dictionary

```python
TOOLS = {
    # ... existing tools ...
    "my_tool": {
        "fn": my_tool,
        "description": "Description of what your tool does",
        "params": {
            "param1": {"type": "string", "description": "First parameter"},
            "param2": {"type": "string", "description": "Second parameter"},
        },
        "required": ["param1"],
    },
}
```

### Step 4: Done!

Your tool is now available in ChatGPT!

## 🔧 Configuration

Edit `constants.py` to customize:

```python
APP_NAME = "Your App Name"
PORT = 8000
MIME_TYPE = "text/html+skybridge"
WIDGET_URI = "ui://widget/testbook-app.html"
```

Or use environment variables:
```bash
export PORT=9000
python mcp_server.py
```

## 🌐 Deployment

### Local Development
```bash
python mcp_server.py
```

### Production (with Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker mcp_server:app
```

### Docker
```bash
docker build -t openaistore .
docker run -p 8000:8000 openaistore
```

## 📊 Architecture Overview

```
ChatGPT
   ↓
MCP Server (FastMCP)
   ├─ list_tools() - Register available tools
   ├─ list_resources() - Provide UI widget
   ├─ handle_call_tool() - Route tool calls
   └─ handle_read_resource() - Serve widget HTML
   ↓
Tool Functions (tools/*.py)
   ├─ say_hello
   ├─ say_goodbye
   └─ Your custom tools
```

For detailed flow diagrams and execution sequences, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## 🧪 Testing Tools

Test a tool locally:

```bash
# Start the server
python mcp_server.py

# In another terminal, test with curl
curl "http://127.0.0.1:8000/tool/say_hello?name=Alice"
```

## 📦 Dependencies

- **fastmcp** - MCP server framework
- **uvicorn** - ASGI server
- **starlette** - Web framework (for CORS)

See `requirements.txt` for all dependencies.

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Tool not showing in ChatGPT | Not registered in TOOLS dict | Verify tool is imported and added to TOOLS |
| Tool call fails | Exception in tool function | Check tool function parameters and return format |
| HTML not rendering | Invalid HTML structure | Validate HTML, check for unclosed tags |
| Port already in use | Another service on port 8000 | Change PORT in constants.py or kill existing process |
| CORS errors | Cross-origin request blocked | Ensure CORS middleware is enabled (automatic in engine.py) |

## 🤝 Contributing

1. Create a new branch for your feature
2. Add your tool following the 4-step process
3. Test thoroughly
4. Commit with clear messages
5. Push and create a pull request

## 📄 License

MIT License - feel free to use and modify

## 📞 Support

For detailed documentation, see [ARCHITECTURE.md](./ARCHITECTURE.md)

---

**Made with ❤️ for Testbook ChatGPT Integration**

