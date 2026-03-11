"""
mcp_server.py – The only file you need to edit to add tools.

1. Write a function in tools/
2. Import it here
3. Add it to TOOLS dict
4. Done.
"""
from mcp_core.engine import create_app
from constants import APP_NAME, PORT

from tools.say_hello import say_hello
from tools.say_goodbye import say_goodbye

# ── Register your tools here ─────────────────────────────────────────────────

TOOLS = {
    "say_hello": {
        "fn":          say_hello,
        "description": "Say hello to someone. Renders a greeting card.",
        "params":      {"name": {"type": "string", "description": "Name to greet"}},
        "required":    ["name"],
    },
    "say_goodbye": {
        "fn":          say_goodbye,
        "description": "Say goodbye to someone. Renders a farewell card.",
        "params":      {"name": {"type": "string", "description": "Name to bid farewell"}},
        "required":    ["name"],
    },
}

# ── That's it. Everything below is just startup. ─────────────────────────────

app = create_app(TOOLS)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting {APP_NAME} on http://127.0.0.1:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

