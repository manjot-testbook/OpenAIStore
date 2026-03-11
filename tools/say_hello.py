"""
tools/say_hello.py – The say_hello tool.
"""


def say_hello(args: dict) -> dict:
    name = args.get("name", "World")

    html = f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:24px;">
      <h1 style="margin:0 0 8px;font-size:28px;">👋 Hello, {name}!</h1>
      <p style="margin:0;color:#a9b4d0;font-size:14px;">Welcome to Testbook ChatGPT App.</p>
      <button onclick='callTool("say_goodbye", {{"name":"{name}"}})'
              style="margin-top:16px;padding:10px 20px;border:none;border-radius:12px;
                     background:linear-gradient(135deg,#7c9cff,#39d0ff);color:#06101f;
                     font-weight:700;font-size:14px;cursor:pointer;">
        Say Goodbye →
      </button>
    </div>
    """

    return {
        "text": f"Hello, {name}!",
        "html": html,
    }

