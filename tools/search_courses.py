"""
tools/search_courses.py – Search Testbook courses/goals via the live Search API.

Calls the Testbook global search endpoint (searchOn=goalCards) in real time,
and returns a rich HTML widget with course cards.  Each card has a "Join Now"
button that links to https://testbook.com/<goalId>-coaching for all platforms.

Super Pass Live is always pinned at the top of every search result.
Its links are fetched once at startup and cached forever.
"""
import json
import logging
import urllib.parse

import httpx

log = logging.getLogger(__name__)

# ── API config ───────────────────────────────────────────────────────────────

_SEARCH_BASE = "https://api.testbook.com/api/v1/search/global"

_PROJECTION = json.dumps({
    "results": {
        "goalCards": {
            "_id": 1,
            "properties": {
                "title": 1, "icon": 1, "cardTitle": 1, "cardDescription": 1,
                "cardIcon": 1, "slug": 1, "heading": 1,
            },
            "isDeListed": 1, "discountPercent": 1, "goalSubs": 1, "stage": 1,
        },
    },
    "searchId": 1,
})

_API_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://testbook.com",
    "Referer": "https://testbook.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    ),
    "x-tb-client": "web,1.2",
}


# ── Super Pass Live — pinned card (fetched once, cached forever) ─────────────

_super_pass_cache: dict | None = None


def _fetch_super_pass() -> dict | None:
    """Fetch Super Pass Live card from the API once and cache it."""
    global _super_pass_cache
    if _super_pass_cache is not None:
        return _super_pass_cache

    try:
        raw_cards = _search_api("Super Pass Live")
        for card in raw_cards:
            props = card.get("properties", {})
            slug = (props.get("slug") or "").strip()
            if slug == "super-pass-live":
                parsed = _parse_card(card)
                if parsed:
                    parsed["url"] = "https://testbook.com/superpass"
                    _super_pass_cache = parsed
                    log.info("Cached Super Pass Live card")
                    return _super_pass_cache
    except Exception as exc:
        log.error("Failed to fetch Super Pass Live: %s", exc)

    return None


# ── API call ─────────────────────────────────────────────────────────────────

def _search_api(term: str) -> list[dict]:
    """
    Call the Testbook search/global API for goalCards.
    Returns the raw list of goalCard dicts from the response.
    """
    params = urllib.parse.urlencode({
        "term": term,
        "searchOn": "goalCards",
        "studentId": "",
        "component": "goal-selection-search",
        "type": "[Goal Selection] searchGoal",
        "__projection": _PROJECTION,
        "language": "English",
    })
    url = f"{_SEARCH_BASE}?{params}"

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=_API_HEADERS)
            resp.raise_for_status()
            data = resp.json()

        return data.get("data", {}).get("results", {}).get("goalCards", [])

    except Exception as exc:
        log.error("Testbook search API error: %s", exc)
        return []


# ── Parse a goalCard into a clean dict ───────────────────────────────────────

def _parse_card(card: dict) -> dict | None:
    """Extract the fields we need from a raw goalCard."""
    if card.get("isDeListed"):
        return None

    # Only include freezed (live/published) goals
    if card.get("stage") != "freezed":
        return None

    props = card.get("properties", {})
    title = (props.get("title") or "").strip()
    slug = (props.get("slug") or "").strip()
    if not title or not slug:
        return None

    # Icon — prefer cardIcon.url, fall back to properties.icon
    card_icon = props.get("cardIcon")
    icon = ""
    if isinstance(card_icon, dict):
        icon = (card_icon.get("url") or "").strip()
    if not icon:
        icon = (props.get("icon") or "").strip()
    if icon.startswith("//"):
        icon = "https:" + icon

    # Universal link for both web and app
    goal_id = card.get("_id", "")
    url = f"https://testbook.com/{goal_id}-coaching"

    # Discount
    discount = card.get("discountPercent")

    return {
        "name": title,
        "id": goal_id,
        "slug": slug,
        "icon": icon,
        "url": url,
        "discount": discount,
    }


# ── HTML widget builder ─────────────────────────────────────────────────────

_DEFAULT_ICON = (
    "https://cdn.testbook.com/resources/productionimages/goal_images/default.png"
)


def _build_card_html(course: dict, index: int = 0) -> str:
    """Build HTML for one course card — orange theme, big Join Now CTA."""
    name = course["name"]
    icon = course["icon"] or _DEFAULT_ICON
    url = course["url"]
    discount = course.get("discount")
    is_super_pass = course.get("slug") == "super-pass-live"

    # Badge: Super Pass gets "₹1 only" in green, others get "X% off" in orange
    badge = ""
    if is_super_pass:
        badge = (
            '<div style="margin-top:4px;">'
            '<span style="background:rgba(16,185,129,0.15);color:#34d399;'
            'font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;'
            'display:inline-block;">₹1 only</span></div>'
        )
    elif discount and int(discount) > 0:
        badge = (
            f'<div style="margin-top:4px;">'
            f'<span style="background:rgba(249,115,22,0.12);color:#fb923c;'
            f'font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;'
            f'display:inline-block;">{discount}% off</span></div>'
        )

    delay = f"{index * 0.08:.2f}s"

    return f"""
    <div class="tb-card" style="background:rgba(255,255,255,0.025);
                border-radius:10px;padding:14px;
                animation:tbFadeUp .4s ease both;animation-delay:{delay};
                transition:background .2s ease;">
      <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px;">
        <img src="{icon}" alt=""
             style="width:36px;height:36px;border-radius:8px;object-fit:cover;
                    background:rgba(255,255,255,0.05);flex-shrink:0;margin-top:1px;"
             onerror="this.style.display='none'"/>
        <div style="flex:1;min-width:0;">
          <div style="font-size:13px;font-weight:500;color:#e2e8f0;
                      line-height:1.4;word-wrap:break-word;">{name}</div>
          {badge}
        </div>
      </div>
      <a href="{url}"
         target="_blank" rel="noopener noreferrer"
         style="display:block;width:100%;padding:10px 0;border-radius:8px;
                background:rgba(249,115,22,0.18);color:#fdba74;
                font-weight:600;font-size:13px;cursor:pointer;text-decoration:none;
                text-align:center;letter-spacing:0.2px;
                border:1px solid rgba(249,115,22,0.3);
                box-sizing:border-box;transition:background .2s ease;">
        Join Now →
      </a>
    </div>"""


# ── Main tool function ───────────────────────────────────────────────────────

def search_courses(args: dict) -> dict:
    """
    MCP tool: search Testbook courses/goals via the live search API.

    args:
        query (str) – what the user is looking for
        limit (int) – max results to return (default 5, max 10)
    """
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 10)

    if not query:
        return {
            "text": "Please provide a search query.",
            "html": _empty_html("Please tell me what course you're looking for."),
        }

    # Hit the Testbook search API
    raw_cards = _search_api(query)

    # Parse and filter
    results: list[dict] = []
    seen_ids: set[str] = set()
    for card in raw_cards:
        parsed = _parse_card(card)
        if parsed and parsed["id"] not in seen_ids:
            results.append(parsed)
            seen_ids.add(parsed["id"])
        if len(results) >= limit:
            break

    # ── Pin Super Pass Live at the top ───────────────────────────────────
    spl = _fetch_super_pass()
    if spl:
        # Remove it from results if already present (avoid duplicates)
        results = [r for r in results if r["id"] != spl["id"]]
        # Prepend it
        results.insert(0, spl)
        # Trim to limit
        results = results[:limit]

    if not results:
        return {
            "text": (
                f"I couldn't find any courses matching '{query}' on Testbook right now. "
                f"Try searching with a different keyword — for example, the exam name "
                f"(like 'SSC CGL', 'UPSC', 'GATE') or subject area."
            ),
            "html": _empty_html(
                f'We couldn\'t find courses matching "<strong>{query}</strong>".'
                "<br/>Try a different search term."
            ),
        }

    # ── Build the results widget ─────────────────────────────────────────
    cards_html = "\n".join(_build_card_html(c, i) for i, c in enumerate(results))
    result_names = ", ".join(c["name"] for c in results)

    html = f"""
    <style>
      @property --tb-angle {{
        syntax: '<angle>';
        initial-value: 0deg;
        inherits: false;
      }}
      @keyframes tbSpin {{
        0%   {{ --tb-angle: 0deg; }}
        100% {{ --tb-angle: 360deg; }}
      }}
      @keyframes tbFadeUp {{
        from {{ opacity:0; transform:translateY(8px); }}
        to   {{ opacity:1; transform:translateY(0); }}
      }}
      @keyframes tbPulse {{
        0%,100% {{ opacity:0.5; }}
        50%     {{ opacity:1; }}
      }}
      .tb-card:hover {{ background:rgba(255,255,255,0.045) !important; }}
      .tb-border {{
        position:relative;
        border-radius:16px;
        max-width:520px;
        font-family:-apple-system,system-ui,sans-serif;
      }}
      .tb-border::before {{
        content:'';
        position:absolute;
        inset:0;
        border-radius:16px;
        padding:1.5px;
        background:conic-gradient(
          from var(--tb-angle),
          transparent 0%,
          #f97316 5%,
          #fb923c 10%,
          #fbbf24 14%,
          transparent 22%,
          transparent 32%,
          rgba(236,72,153,0.7) 35%,
          rgba(168,85,247,0.5) 39%,
          transparent 44%,
          transparent 56%,
          rgba(255,255,255,0.45) 58%,
          rgba(192,132,252,0.35) 61%,
          transparent 66%,
          transparent 80%,
          rgba(249,115,22,0.35) 84%,
          transparent 90%,
          transparent 100%
        );
        -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite:xor;
        mask-composite:exclude;
        animation:tbSpin 4s cubic-bezier(0.68, 0, 0.27, 1) infinite;
        pointer-events:none;
      }}
    </style>
    <div class="tb-border">
      <div style="background:#0f1117;border-radius:16px;overflow:hidden;">

        <div style="padding:20px;">

          <!-- Header -->
          <div style="margin-bottom:16px;animation:tbFadeUp .35s ease both;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <div style="width:6px;height:6px;border-radius:50%;background:#f97316;
                          animation:tbPulse 2s ease-in-out infinite;"></div>
              <span style="font-size:11px;font-weight:600;color:#f97316;
                           text-transform:uppercase;letter-spacing:0.8px;">
                Courses
              </span>
            </div>
            <h2 style="margin:0;font-size:17px;font-weight:600;color:#f1f5f9;
                       line-height:1.3;">
              Results for "{query}"
            </h2>
            <p style="margin:4px 0 0;font-size:12px;color:#64748b;">
              {len(results)} course{"s" if len(results) != 1 else ""} found
            </p>
          </div>

          <!-- Cards -->
          <div style="display:flex;flex-direction:column;gap:8px;">
            {cards_html}
          </div>

          <!-- Footer -->
          <div style="margin-top:14px;text-align:center;
                      animation:tbFadeUp .4s ease both;animation-delay:.5s;">
            <a href="https://testbook.com" target="_blank" rel="noopener noreferrer"
               style="font-size:11px;color:#475569;text-decoration:none;">
              Powered by Testbook
            </a>
          </div>

        </div>

      </div>
    </div>"""

    text = _build_text_response(query, results)
    return {"text": text, "html": html}


def _build_text_response(query: str, results: list[dict]) -> str:
    """Build a conversational text response that ChatGPT can use to frame its answer."""
    count = len(results)
    names = [r["name"] for r in results]

    # Highlight courses with discounts
    discounted = [r for r in results if r.get("discount") and int(r["discount"]) > 0]

    lines = [
        f"Here are {count} recommended Testbook courses for '{query}':\n",
    ]

    for i, r in enumerate(results, 1):
        entry = f"{i}. **{r['name']}**"
        if r.get("discount") and int(r["discount"]) > 0:
            entry += f" — currently {r['discount']}% off!"
        lines.append(entry)

    lines.append("")

    if discounted:
        best = max(discounted, key=lambda x: int(x["discount"]))
        lines.append(
            f"💡 Best deal right now: **{best['name']}** at {best['discount']}% off."
        )

    lines.append(
        "\nEach course includes live classes, study material, test series, and more. "
        "Tap 'Explore & Buy' on any card above to get started!"
    )

    return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_html(message: str) -> str:
    return f"""
    <style>
      @property --tb-angle {{
        syntax: '<angle>';
        initial-value: 0deg;
        inherits: false;
      }}
      @keyframes tbSpin {{
        0%   {{ --tb-angle: 0deg; }}
        100% {{ --tb-angle: 360deg; }}
      }}
      .tb-border {{
        position:relative;
        border-radius:16px;
        max-width:520px;
        font-family:-apple-system,system-ui,sans-serif;
      }}
      .tb-border::before {{
        content:'';
        position:absolute;
        inset:0;
        border-radius:16px;
        padding:1.5px;
        background:conic-gradient(
          from var(--tb-angle),
          transparent 0%, #f97316 5%, #fb923c 10%, transparent 22%,
          transparent 55%, rgba(236,72,153,0.7) 58%, transparent 64%,
          transparent 100%
        );
        -webkit-mask:linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite:xor;
        mask-composite:exclude;
        animation:tbSpin 4s cubic-bezier(0.68, 0, 0.27, 1) infinite;
        pointer-events:none;
      }}
    </style>
    <div class="tb-border">
      <div style="background:#0f1117;border-radius:16px;overflow:hidden;">
        <div style="padding:32px 20px;text-align:center;">
          <div style="font-size:32px;margin-bottom:12px;opacity:0.5;">🔍</div>
          <p style="margin:0;font-size:14px;font-weight:500;color:#94a3b8;
                    line-height:1.5;">{message}</p>
        </div>
      </div>
    </div>"""

