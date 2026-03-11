"""
tools/say_goodbye.py – The say_goodbye tool.
"""


def say_goodbye(args: dict) -> dict:
    name = args.get("name", "World")

    html = f"""
    <div style="background:linear-gradient(135deg,#2a0911,#1a1a2e);
                border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:24px;">
      <h1 style="margin:0 0 8px;font-size:28px;">👋 Goodbye, {name}!</h1>
      <p style="margin:0;color:#a9b4d0;font-size:14px;">See you next time on Testbook.</p>
      <button onclick='callTool("say_hello", {{"name":"{name}"}})'
              style="margin-top:16px;padding:10px 20px;border:none;border-radius:12px;
                     background:linear-gradient(135deg,#fb7185,#f43f5e);color:#2a0911;
                     font-weight:700;font-size:14px;cursor:pointer;">
        ← Say Hello Again
      </button>
    </div>
    """

    return {
        "text": f"Goodbye, {name}!",
        "html": html,
    }

