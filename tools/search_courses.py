"""
tools/search_courses.py – Search Testbook courses/goals via live API.

Fetches the full goal catalogue from the Testbook API, caches it in memory,
and does token-based fuzzy search to return the best matches as a rich
HTML widget with "Buy Course" buttons.
"""
import logging
import time
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

# ── API config ───────────────────────────────────────────────────────────────

_GOALS_API = (
    "https://api.testbook.com/api/v1/goals"
    "?fields=_id,properties.title,properties.icon,properties.slug,isDeListed"
    "&isAdminReq=true&language=English"
)

_API_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://testbook.com",
    "Referer": "https://testbook.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "x-tb-client": "web,1.2",
}

_CACHE_TTL = 600  # seconds – refresh catalogue every 10 min

# ── In-memory cache ──────────────────────────────────────────────────────────

_courses: list[dict[str, str]] = []
_cache_ts: float = 0.0


def _fetch_courses() -> list[dict[str, str]]:
    """
    Hit the Testbook goals API and return a clean list of active courses.
    Each dict: {"name", "id", "slug", "url", "icon"}
    """
    global _courses, _cache_ts

    now = time.time()
    if _courses and (now - _cache_ts) < _CACHE_TTL:
        return _courses

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(_GOALS_API, headers=_API_HEADERS)
            resp.raise_for_status()
            data = resp.json()

        goals = data.get("data", {}).get("goals", [])

        results: list[dict[str, str]] = []
        for g in goals:
            # Skip delisted / inactive goals
            if g.get("isDeListed"):
                continue

            props = g.get("properties", {})
            title = (props.get("title") or "").strip()
            slug = (props.get("slug") or "").strip()
            icon = (props.get("icon") or "").strip()

            if not title or not slug:
                continue

            # Normalise protocol-relative icon URLs
            if icon.startswith("//"):
                icon = "https:" + icon

            results.append({
                "name": title,
                "id":   g.get("_id", ""),
                "slug": slug,
                "url":  f"https://testbook.com/{slug}",
                "icon": icon,
            })

        if results:
            _courses = results
            _cache_ts = now
            log.info("Fetched %d active courses from Testbook API", len(results))
        else:
            log.warning("API returned 0 active courses, keeping stale cache")

    except Exception as exc:
        log.error("Failed to fetch courses from API: %s", exc)
        # If cache is empty AND API fails, fall back to CSV
        if not _courses:
            _courses = _load_csv_fallback()
            _cache_ts = now

    return _courses


# ── CSV fallback (in case the API is unreachable on first boot) ──────────────

_CSV_PATH = Path(__file__).resolve().parent.parent / "assets" / "goalDetails.csv"


def _load_csv_fallback() -> list[dict[str, str]]:
    """Last-resort: read the old goalDetails.csv."""
    import csv
    log.warning("Falling back to CSV catalogue at %s", _CSV_PATH)
    rows: list[dict[str, str]] = []
    try:
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append({
                    "name": (row.get("goalName") or "").strip(),
                    "id":   (row.get("goalId") or "").strip(),
                    "slug": "",
                    "url":  (row.get("URL") or "").strip(),
                    "icon": (row.get("ICON") or "").strip(),
                })
    except FileNotFoundError:
        pass
    return rows


# ── Scoring / search ─────────────────────────────────────────────────────────

def _score_field(query_tokens: list[str], full_query: str, text: str) -> int:
    """Score a single text field against query tokens."""
    score = 0
    matched_tokens = 0
    for token in query_tokens:
        if token in text:
            score += 10
            matched_tokens += 1
            if text.startswith(token):
                score += 5
    # Bonus: full query appears as substring
    if full_query in text:
        score += 20
    # Bonus: exact match
    if text == full_query:
        score += 50
    # Bonus: ALL tokens matched (very relevant)
    if matched_tokens == len(query_tokens) and matched_tokens > 1:
        score += 15
    return score


def _match_score(query_tokens: list[str], course: dict[str, str]) -> int:
    """Score a course against search tokens, checking title AND slug."""
    full_query = " ".join(query_tokens)
    name_lower = course["name"].lower()
    # Treat slug hyphens as spaces for matching (e.g. "ssc-cgl" → "ssc cgl")
    slug_lower = course.get("slug", "").lower().replace("-", " ")

    title_score = _score_field(query_tokens, full_query, name_lower)
    slug_score = _score_field(query_tokens, full_query, slug_lower)

    # Take the best of both, but give a small bonus if both match
    best = max(title_score, slug_score)
    if title_score > 0 and slug_score > 0:
        best += 5
    return best


def _search(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Fuzzy-search courses by query string, return top matches."""
    courses = _fetch_courses()
    query_lower = query.lower().strip()
    if not query_lower:
        return courses[:limit]

    query_tokens = query_lower.split()

    scored = []
    for c in courses:
        score = _match_score(query_tokens, c)
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


# ── HTML widget builder ──────────────────────────────────────────────────────

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


# ── Main tool function ───────────────────────────────────────────────────────

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

