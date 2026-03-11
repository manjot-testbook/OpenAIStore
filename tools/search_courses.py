"""
tools/search_courses.py – Search Testbook courses/goals and return a widget with Buy buttons.
"""
import csv
from pathlib import Path

# ── Load the CSV once at import time ─────────────────────────────────────────

_CSV_PATH = Path(__file__).resolve().parent.parent / "assets" / "goalDetails.csv"
_COURSES: list[dict[str, str]] = []


def _load_courses() -> list[dict[str, str]]:
    """Read goalDetails.csv into a list of dicts (cached)."""
    global _COURSES
    if _COURSES:
        return _COURSES
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _COURSES.append({
                "name": (row.get("goalName") or "").strip(),
                "id":   (row.get("goalId") or "").strip(),
                "url":  (row.get("URL") or "").strip(),
                "icon": (row.get("ICON") or "").strip(),
            })
    return _COURSES


def _match_score(query_tokens: list[str], name_lower: str) -> int:
    """
    Simple scoring: count how many query tokens appear in the course name.
    Gives bonus for exact substring match.
    """
    score = 0
    for token in query_tokens:
        if token in name_lower:
            score += 10
            # Bonus if it starts with the token
            if name_lower.startswith(token):
                score += 5
    # Bonus for exact full query match
    full_query = " ".join(query_tokens)
    if full_query in name_lower:
        score += 20
    if name_lower == full_query:
        score += 50
    return score


def _search(query: str, limit: int = 5) -> list[dict]:
    """Fuzzy-search courses by query string, return top matches."""
    courses = _load_courses()
    query_lower = query.lower().strip()
    if not query_lower:
        return courses[:limit]

    query_tokens = query_lower.split()

    scored = []
    for c in courses:
        name_lower = c["name"].lower()
        score = _match_score(query_tokens, name_lower)
        if score > 0:
            scored.append((score, c))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


# ── Default placeholder icon ─────────────────────────────────────────────────
_DEFAULT_ICON = "https://cdn.testbook.com/resources/productionimages/goal_images/default.png"


def _build_card_html(course: dict) -> str:
    """Build HTML for a single course card."""
    name = course["name"]
    url = course["url"]
    icon = course["icon"] if course["icon"] else _DEFAULT_ICON

    return f"""
    <div style="display:flex;align-items:center;gap:14px;
                background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                border-radius:14px;padding:14px 16px;transition:transform .15s;">
      <img src="{icon}" alt=""
           style="width:56px;height:56px;border-radius:10px;object-fit:cover;
                  background:#1e293b;flex-shrink:0;"
           onerror="this.style.display='none'"/>
      <div style="flex:1;min-width:0;">
        <div style="font-size:15px;font-weight:600;color:#f1f5f9;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {name}
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-top:2px;">Testbook SuperCoaching</div>
      </div>
      <a href="{url}" target="_blank" rel="noopener noreferrer"
         style="flex-shrink:0;padding:9px 18px;border:none;border-radius:10px;
                background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;
                font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;
                display:inline-block;text-align:center;">
        Buy Course
      </a>
    </div>"""


def search_courses(args: dict) -> dict:
    """
    MCP tool: search Testbook courses/goals.

    args:
        query (str) – what the user is looking for (e.g. "ssc cgl", "banking", "gate")
        limit (int) – max results to return (default 5, max 10)
    """
    query = args.get("query", "")
    limit = min(int(args.get("limit", 5)), 10)

    results = _search(query, limit=limit)

    if not results:
        html = f"""
        <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                    border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:28px;
                    text-align:center;">
          <div style="font-size:40px;margin-bottom:12px;">🔍</div>
          <h2 style="margin:0 0 6px;font-size:20px;color:#f1f5f9;">No courses found</h2>
          <p style="margin:0;color:#94a3b8;font-size:14px;">
            We couldn't find courses matching "<strong>{query}</strong>".<br/>
            Try a different search term.
          </p>
        </div>"""
        return {"text": f"No courses found for '{query}'.", "html": html}

    # ── Build the results widget ─────────────────────────────────────────
    cards_html = "\n".join(_build_card_html(c) for c in results)
    result_names = ", ".join(c["name"] for c in results)

    html = f"""
    <div style="background:linear-gradient(135deg,#0f172a,#1e293b);
                border:1px solid rgba(255,255,255,0.08);border-radius:18px;
                padding:24px;max-width:520px;">
      <!-- Header -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
        <div style="font-size:28px;">📚</div>
        <div>
          <h2 style="margin:0;font-size:18px;color:#f1f5f9;">
            Testbook Courses
          </h2>
          <p style="margin:2px 0 0;font-size:13px;color:#64748b;">
            {len(results)} result{"s" if len(results) != 1 else ""} for "<strong style="color:#94a3b8;">{query}</strong>"
          </p>
        </div>
      </div>

      <!-- Course Cards -->
      <div style="display:flex;flex-direction:column;gap:10px;">
        {cards_html}
      </div>

      <!-- Footer -->
      <div style="margin-top:16px;text-align:center;">
        <a href="https://testbook.com" target="_blank" rel="noopener noreferrer"
           style="font-size:12px;color:#64748b;text-decoration:none;">
          Explore all courses on testbook.com →
        </a>
      </div>
    </div>"""

    text = f"Found {len(results)} course(s) for '{query}': {result_names}."
    return {"text": text, "html": html}

