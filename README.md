# Testbook ChatGPT MCP App

## Project Structure

```
OpenAIStore/
├── mcp_server.py       ← THE file you edit. Import tools, add to TOOLS dict, done.
├── constants.py        ← All config variables.
├── mcp_core/
│   └── engine.py       ← MCP boilerplate. Never touch this.
└── tools/              ← One file per tool. Function + its HTML.
    ├── say_hello.py
    └── say_goodbye.py
```

## How to add a new tool

**Step 1** — Create `tools/my_tool.py`:

```python
def my_tool(args: dict) -> dict:
    name = args.get("name", "World")
    return {
        "text": f"Hey {name}",                       # plain text for ChatGPT
        "html": f"<h1>Hey {name}</h1>",              # rendered in the widget
    }
```

**Step 2** — Open `mcp_server.py`, import it, add it to the dict:

```python
from tools.my_tool import my_tool

TOOLS = {
    # ...existing tools...
    "my_tool": {
        "fn":          my_tool,
        "description": "Does my thing",
        "params":      {"name": {"type": "string"}},
        "required":    ["name"],
    },
}
```

**Step 3** — There is no step 3. Run `python mcp_server.py`.

## How to run

```bash
pip install mcp fastmcp uvicorn starlette pydantic requests
python mcp_server.py
# → http://127.0.0.1:8000
```

