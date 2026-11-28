# First collection source: Sportradar Odds Comparison v2

## Why this is the first source

Start with Sportradar Odds Comparison v2 as the first aggregator integration, rather than scraping one sportsbook site. Its documented Odds Comparison Core tier provides access to 140+ global bookmakers and 30+ sports, subject to the account's configured coverage. The v2 product is split into Prematch, Player Props, Futures and Live Odds packages with a shared event/market/book/outcome data model. This is a practical first source for building the universal ingestion pipeline.

Official references:
- API overview: https://developer.sportradar.com/odds/reference/intro
- Integration guide: https://developer.sportradar.com/odds/docs/oc-ig-overview
- API basics and discovery feeds: https://developer.sportradar.com/odds/docs/oc-ig-api-basics
- Market model: https://developer.sportradar.com/odds/docs/oc-ig-fundamentals
- Global Core tier: https://developer.sportradar.com/odds/reference/oc-core-overview
- Live Odds overview: https://developer.sportradar.com/odds/reference/oc-live-odds-overview

The implementation now uses the documented Prematch v2 Books, Sports, Sport Competitions,
Competition Schedules, Sport Event Markets and pagination headers. It retains bookmaker
identity on each market snapshot, along with the original market/book/outcome payloads.

This does not mean Sportradar includes every bookmaker in every country or every market
on every event. The account's Books, Sports and Competition discovery feeds determine
actual coverage. OC Core is enabled at the API-key level by Sportradar Support; inspect
the X-Origin-Id response header rather than assuming global-core access. Direct 1xBet
and PariPesa adapters can be added later if the aggregator does not cover them or their
market depth is insufficient.

## Collection flow

### A. Discover provider coverage
1. Keep the API key server-side in an environment variable; never commit it or send it to the mobile client.
2. Call the Books feed to record which bookmakers this key can see.
3. Call Sports and Sport Competitions feeds to discover sports and competitions, including whether prematch markets, futures and player props are available.
4. Save provider coverage snapshots with retrieval timestamps.

### B. Discover events
1. Use the relevant daily schedule feed for each supported sport/competition.
2. Store source event ID, sport, competition, participants, start time, and event status.
3. Use source IDs as the primary event identity; use team/time matching only as a secondary cross-provider mapping method.

### C. Collect every available market
1. For each event, request the event's market feed in every entitled package: Prematch, Player Props, Futures where applicable, and Live Odds for in-play events.
2. Preserve every returned market instance, bookmaker, outcome, line/handicap, odds format, opening price and source status.
3. Treat the feed as the authoritative inventory for that provider snapshot. Do not replace it with a hand-written list of common market names.
4. Retain unfamiliar market IDs and labels as unclassified records. Never drop them just because the analysis engine does not understand them yet.
5. Process market removals/changes and keep timestamped snapshots so suspended, removed, stale and price-changed markets are visible.

### D. Normalize without losing detail
Canonical identity should include sport, event, provider, market ID/name, period, participant, line/handicap, selection ID/name and settlement definition. Preserve original source fields beside canonical fields. Two selections are comparable only if their settlement rules and all relevant dimensions match.

### E. Analyse and compare
The collection service and analysis service remain separate. Ingestion stores the raw market inventory first. Market-specific models then add probabilities only when they have adequate data. Compare odds across books, calculate implied probabilities and overround where valid, and flag stale or suspended prices. Unsupported markets remain visible with "not yet modelled".

## Reliability, cost and safety
- Respect provider polling/update-frequency guidance and use change feeds where offered; do not poll every endpoint continuously.
- Retry transient failures with bounded backoff; record rate limits and provider outages.
- Make ingestion idempotent using provider IDs and snapshot timestamps.
- Keep API keys in deployment secrets; redact them from logs.
- Use only the licensed API products and account entitlements. Do not bypass access controls or scrape restricted sportsbook pages.
- Build a provider health/coverage report: books available, sports/competitions available, events scanned, markets and selections received, unknown markets, last successful poll, and feed age.

## First milestone acceptance criteria
- API key is configured without being committed.
- Books, Sports and Competition discovery can be fetched and stored.
- One selected event can be traced from schedule to the available Prematch market board.
- Every returned Prematch market/book/outcome instance is persisted, including unknown market types.
- Snapshot timestamps and source identifiers are retained.
- A coverage report shows exactly what was and was not returned.
- The raw discovery inventory shows exactly which bookmaker IDs/names and competition IDs the key exposed.
- No predictions are generated for markets without a suitable model and inputs.

## Commercial and regional checks before choosing production
Sportradar's published global tier is a strong candidate, but actual bookmaker coverage, including 1xBet and PariPesa, must be confirmed with the provider for the intended Nigerian account/region and plan. Live Odds access may require a separate entitlement. Confirm pricing, usage limits, redistribution rights and permitted end-user display before production use.
