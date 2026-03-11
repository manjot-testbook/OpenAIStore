"""
tools/search_courses.py – Search Testbook courses/goals via the live Search API.

Calls the Testbook global search endpoint (searchOn=goalCards) in real time,
and returns a rich HTML widget with course cards.  Each card has a "Buy Course"
button whose href is device-aware:
  • Desktop / web  → testbook.com/{slug}
  • Android app    → testbook://tbapp/landing/super?goalId={id}

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
                "pitchCarousel": {
                    "url": 1, "webLink": 1, "deeplink": 1, "type": 1,
                },
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
                    parsed["web_link"] = "https://testbook.com/superpass"
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

    # Web link: just the goal landing page
    goal_id = card.get("_id", "")
    web_link = f"https://testbook.com/{slug}"

    # Deep link: standard app deeplink format
    deep_link = f"testbook://tbapp/landing/super?goalId={goal_id}"

    # Discount
    discount = card.get("discountPercent")

    return {
        "name": title,
        "id": goal_id,
        "slug": slug,
        "icon": icon,
        "web_link": web_link,
        "deep_link": deep_link,
        "discount": discount,
    }


# ── HTML widget builder ─────────────────────────────────────────────────────

_DEFAULT_ICON = (
    "https://cdn.testbook.com/resources/productionimages/goal_images/default.png"
)


def _build_card_html(course: dict) -> str:
    """Build HTML for one course card with device-aware Buy button."""
    name = course["name"]
    icon = course["icon"] or _DEFAULT_ICON
    web_link = course["web_link"]
    deep_link = course["deep_link"]
    discount = course.get("discount")

    discount_badge = ""
    if discount and int(discount) > 0:
        discount_badge = (
            f'<span style="background:#ef4444;color:#fff;font-size:11px;'
            f'font-weight:700;padding:2px 7px;border-radius:6px;margin-left:8px;">'
            f'{discount}% OFF</span>'
        )

    # JS onclick: Android → deeplink, else → webLink
    return f"""
    <div style="display:flex;align-items:center;gap:14px;
                background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                border-radius:14px;padding:14px 16px;">
      <img src="{icon}" alt=""
           style="width:56px;height:56px;border-radius:10px;object-fit:cover;
                  background:#1e293b;flex-shrink:0;"
           onerror="this.style.display='none'"/>
      <div style="flex:1;min-width:0;">
        <div style="font-size:15px;font-weight:600;color:#f1f5f9;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {name}{discount_badge}
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-top:2px;">Testbook SuperCoaching</div>
      </div>
      <a href="{web_link}"
         data-deeplink="{deep_link}"
         onclick="(function(e){{var u=/Android/i.test(navigator.userAgent)?e.currentTarget.dataset.deeplink:e.currentTarget.href;window.open(u,'_blank');e.preventDefault()}})(event)"
         target="_blank" rel="noopener noreferrer"
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
            "text": f"No courses found for '{query}'.",
            "html": _empty_html(
                f'We couldn\'t find courses matching "<strong>{query}</strong>".'
                "<br/>Try a different search term."
            ),
        }

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
            {len(results)} result{"s" if len(results) != 1 else ""} for
            "<strong style="color:#94a3b8;">{query}</strong>"
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


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_html(message: str) -> str:
    return f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:28px;
                text-align:center;">
      <div style="font-size:40px;margin-bottom:12px;">🔍</div>
      <h2 style="margin:0 0 6px;font-size:20px;color:#f1f5f9;">No courses found</h2>
      <p style="margin:0;color:#94a3b8;font-size:14px;">{message}</p>
    </div>"""

