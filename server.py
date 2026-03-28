"""
Filmweb MCP Server — wyszukiwanie filmów, oceny, opisy z Filmweb.pl
"""

import asyncio
import json
import urllib.request
import urllib.parse
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_URL = "https://www.filmweb.pl/api/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

GENRE_MAP = {
    "animacja": 2, "animated": 2, "biograficzny": 3, "biography": 3,
    "dla dzieci": 4, "children": 4, "historyczny": 11, "historical": 11,
    "horror": 12, "horrors": 12,
    "komedia": 13, "comedy": 13, "komedii": 13,
    "kryminał": 15, "crime": 15, "kryminalny": 15,
    "melodramat": 16, "musical": 17,
    "obyczajowy": 19, "przygodowy": 20, "adventure": 20,
    "sensacyjny": 22, "action": 28, "akcja": 28, "akcji": 28,
    "thriller": 24, "thrillers": 24,
    "western": 25, "wojenny": 26, "war": 26,
    "romans": 32, "romance": 32, "romantyczny": 32,
    "sci-fi": 33, "science fiction": 33, "science-fiction": 33, "sf": 33, "scifi": 33,
    "dramat": 37, "drama": 37,
    "psychologiczny": 38, "psychological": 38,
    "katastroficzny": 40, "disaster": 40,
    "fantasy": 42, "fantastyczny": 42,
    "dokumentalny": 47, "documentary": 47, "dokument": 47,
}

app = Server("filmweb-mcp")


def _get(path: str) -> dict | list | None:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode())
    except Exception:
        pass
    return None


def _search(query: str, min_rating: float = 0, year: int = 0, year_from: int = 0, min_votes: int = 0, limit: int = 5) -> str:
    query_lower = query.lower().strip()
    genre_id = None
    for genre_name, gid in GENRE_MAP.items():
        if genre_name in query_lower:
            genre_id = gid
            break

    if genre_id or year or year_from or min_rating or min_votes:
        params = ["query="]
        if genre_id:
            params.append(f"genreIds={genre_id}")
        if year:
            params.append(f"startYear={year}&endYear={year}")
        elif year_from:
            params.append(f"startYear={year_from}")
        if min_votes:
            params.append(f"startCount={int(min_votes)}")

        # Paginacja z page (1-indexed, 10 wyników na stronę)
        all_hits = []
        max_pages = min(10, (limit * 3) // 10 + 1)
        for page in range(1, max_pages + 1):
            page_params = params + [f"page={page}"]
            data = _get(f"/films/search?{'&'.join(page_params)}")
            if not data or not data.get("searchHits"):
                break
            new_hits = data["searchHits"]
            all_hits.extend(new_hits)
            if len(new_hits) < 10:
                break

        if all_hits:
            # Deduplikacja po ID
            seen_ids = set()
            unique_hits = []
            for h in all_hits:
                fid = h.get("id")
                if fid not in seen_ids:
                    seen_ids.add(fid)
                    unique_hits.append(h)

            results = []
            for h in unique_hits:
                if len(results) >= limit:
                    break
                fid = h.get("id")
                info = _get(f"/title/{fid}/info") or _get(f"/film/{fid}/info") or {}
                rating_data = _get(f"/film/{fid}/rating") or {}
                title = info.get("title", f"Film {fid}")
                film_year = info.get("year", "?")
                rate = round(float(rating_data.get("rate", 0)), 1)
                votes = int(rating_data.get("count", 0))
                if min_rating and rate < min_rating:
                    continue
                results.append(f"- {title} ({film_year}) — {rate}/10 ({votes} głosów) [id:{fid}]")

            header = f"Wyniki"
            if genre_id:
                header += f" [{query}]"
            if year:
                header += f" (rok {year})"
            elif year_from:
                header += f" (od {year_from})"
            if min_rating:
                header += f" (ocena >= {min_rating})"
            if min_votes:
                header += f" (min {min_votes} głosów)"
            header += f" — {data.get('total', '?')} w bazie"
            return header + ":\n" + "\n".join(results) if results else "Brak wyników spełniających kryteria."

    encoded = urllib.parse.quote(query)
    data = _get(f"/live/search?query={encoded}")
    if not data:
        return f"Brak wyników dla '{query}'"

    hits = data.get("searchHits", []) if isinstance(data, dict) else data
    results = []
    for item in hits[:limit]:
        if not isinstance(item, dict) or (item.get("type", "film") != "film" and "type" in item):
            continue
        fid = item.get("id")
        if not fid:
            continue
        title = item.get("matchedTitle", "?")
        info = _get(f"/film/{fid}/info") or {}
        rating_data = _get(f"/film/{fid}/rating") or {}
        film_year = info.get("year", "?")
        rate = round(float(rating_data.get("rate", 0)), 1)
        votes = int(rating_data.get("count", 0))
        if min_rating and rate < min_rating:
            continue
        results.append(f"- {title} ({film_year}) — {rate}/10 ({votes} głosów) [id:{fid}]")

    return f"Wyniki dla '{query}':\n" + "\n".join(results) if results else f"Brak wyników dla '{query}'"


def _info(film_id: int) -> str:
    info = _get(f"/film/{film_id}/info") or _get(f"/title/{film_id}/info")
    if not info:
        return f"Nie znaleziono filmu o id {film_id}"
    title = info.get("title", "?")
    original_title = info.get("originalTitle", "")
    year = info.get("year", "?")
    duration = info.get("duration", "?")
    rating_data = _get(f"/film/{film_id}/rating") or {}
    rating = round(float(rating_data.get("rate", 0)), 1)
    votes = int(rating_data.get("count", 0))
    desc_data = _get(f"/film/{film_id}/description") or {}
    synopsis = desc_data.get("synopsis", "Brak opisu")
    if len(synopsis) > 400:
        synopsis = synopsis[:400] + "..."
    result = f"{title}"
    if original_title and original_title != title:
        result += f" ({original_title})"
    result += f"\nRok: {year} | Czas: {duration} min | Ocena: {rating}/10 ({votes} głosów)"
    result += f"\n\n{synopsis}"
    return result


# --- MCP Tool definitions ---

TOOLS = [
    Tool(
        name="filmweb_search",
        description="Search Filmweb.pl with filters. Use genre name as query (horror, sci-fi, thriller, komedia, dramat) with year/min_rating/min_votes.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Genre name or movie title"},
                "min_rating": {"type": "number", "description": "Minimum rating 1-10"},
                "year": {"type": "number", "description": "Exact year"},
                "year_from": {"type": "number", "description": "Films from this year onwards"},
                "min_votes": {"type": "number", "description": "Minimum vote count (10000=popular)"},
                "limit": {"type": "number", "description": "Max results (default 5)"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="filmweb_info",
        description="Get movie details: title, year, duration, rating, synopsis.",
        inputSchema={
            "type": "object",
            "properties": {
                "film_id": {"type": "number", "description": "Filmweb movie ID from search"},
            },
            "required": ["film_id"],
        },
    ),
    Tool(
        name="filmweb_rating",
        description="Get movie rating and vote count.",
        inputSchema={
            "type": "object",
            "properties": {
                "film_id": {"type": "number", "description": "Filmweb movie ID"},
            },
            "required": ["film_id"],
        },
    ),
    Tool(
        name="filmweb_person",
        description="Get actor/director info by person ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "person_id": {"type": "number", "description": "Filmweb person ID"},
            },
            "required": ["person_id"],
        },
    ),
    Tool(
        name="filmweb_vod",
        description="List VOD platforms in Poland.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="filmweb_genres",
        description="List available genre names for search.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "filmweb_search":
        result = await asyncio.to_thread(
            _search, arguments["query"],
            min_rating=float(arguments.get("min_rating", 0)),
            year=int(arguments.get("year", 0)),
            year_from=int(arguments.get("year_from", 0)),
            min_votes=int(arguments.get("min_votes", 0)),
            limit=int(arguments.get("limit", 5)),
        )
    elif name == "filmweb_info":
        result = await asyncio.to_thread(_info, int(arguments["film_id"]))
    elif name == "filmweb_rating":
        data = _get(f"/film/{int(arguments['film_id'])}/rating")
        info = _get(f"/film/{int(arguments['film_id'])}/info") or {}
        if data:
            result = f"{info.get('title', '?')}: {round(float(data.get('rate', 0)), 1)}/10 ({int(data.get('count', 0))} głosów)"
        else:
            result = "Brak oceny"
    elif name == "filmweb_person":
        data = _get(f"/person/{int(arguments['person_id'])}/info")
        result = f"{data.get('name', '?')}" if data else "Nie znaleziono"
    elif name == "filmweb_vod":
        data = _get("/vod/providers/list") or []
        result = "VOD w Polsce: " + ", ".join(d.get("name", "?") for d in data[:15])
    elif name == "filmweb_genres":
        genres = sorted(set(f"{n}" for n, _ in GENRE_MAP.items() if not n.isascii() or n in ("horror", "thriller", "drama", "comedy", "action", "sci-fi", "fantasy", "romance", "western", "war")))
        result = "Gatunki: " + ", ".join(genres)
    else:
        result = f"Nieznane: {name}"

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
