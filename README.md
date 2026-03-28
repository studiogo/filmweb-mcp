# Filmweb MCP Server

MCP server for searching movies on [Filmweb.pl](https://www.filmweb.pl) — Poland's largest movie database.

Search by genre, year, rating, vote count. Get movie details, ratings, synopses, actor info, and VOD platform availability.

## Tools

| Tool | Description |
|---|---|
| `filmweb_search` | Search movies with filters: genre, year, min rating, min votes |
| `filmweb_info` | Get movie details: title, year, duration, rating, synopsis |
| `filmweb_rating` | Get movie rating and vote count |
| `filmweb_person` | Get actor/director info |
| `filmweb_vod` | List VOD platforms in Poland |
| `filmweb_genres` | List available genre names |

## Examples

```
filmweb_search(query="horror", year_from=2018, min_votes=10000)
→ Lighthouse (2019) — 7.5/10 (77k votes), Substancja (2024) — 6.7/10 (108k votes)...

filmweb_search(query="sci-fi", min_rating=7.5, year=2023, min_votes=10000)
→ Spider-Man: Poprzez multiwersum (2023) — 8.0/10 (59k votes)...

filmweb_info(film_id=628)
→ Matrix (The Matrix), 1999, 7.6/10 (865k votes), synopsis...
```

## Install in Claude Code

Add to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "filmweb": {
      "command": "python",
      "args": ["/path/to/filmweb-mcp/server.py"]
    }
  }
}
```

Or with uv (no install needed):

```json
{
  "mcpServers": {
    "filmweb": {
      "command": "uv",
      "args": ["run", "--with", "mcp", "/path/to/filmweb-mcp/server.py"]
    }
  }
}
```

## Supported Genres

horror, komedia, thriller, dramat, sci-fi, akcja, romans, western, fantasy, kryminał, animacja, dokumentalny, przygodowy, wojenny, musical, biograficzny, psychologiczny, katastroficzny, melodramat, obyczajowy

English names also work: comedy, action, crime, romance, adventure, war, documentary, drama, thriller, horror, sci-fi, fantasy.

## License

MIT
