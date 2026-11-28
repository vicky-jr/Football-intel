# Global bookmaker and market coverage strategy

## Product requirement

Football Intel must be bookmaker-agnostic and multi-sport. It must not be limited to Football.com, football, Nigeria, or a fixed shortlist of market types.

The target is to discover and analyse the complete market inventory exposed for each event by every bookmaker/data source that has been successfully connected and verified. The system must be designed to scale to a catalogue containing 100,000+ distinct market/selection definitions across sports, operators, competitions and event types.

That scale is a catalogue and discovery requirement, not a promise that 100,000 options are simultaneously offered for one match. The live inventory for a particular event is the exact set returned by each bookmaker at the time of collection.

Examples of operators explicitly in scope include 1xBet and PariPesa/Paripesa, alongside popular regional and international bookmakers. The provider registry must be extensible; the initial seed list is not the boundary of the product.

## Market discovery, not a hard-coded checklist

Do not attempt to manually enumerate a supposedly complete universal list of 100,000 options. Market names and settlement rules vary by operator, sport, competition, event, jurisdiction and time.

Instead, every provider adapter must enumerate the full event market catalogue exposed by its authorised source, including:
- all market families and sub-markets;
- every line, handicap, total, period, segment and special;
- every selection/outcome under each market;
- player/team/participant props where supplied;
- pre-match and in-play markets when available;
- market state (open, suspended, closed, settled or unavailable);
- odds, source timestamp and retrieval timestamp.

The system must retain the provider's original market and selection labels/IDs, then map them to canonical definitions without losing source detail. Equivalent options may be compared only when sport, event, participant, period, line, selection and settlement rules match.

## Provider registry

Each operator is an independently enabled provider with its own adapter and status:
- discovered;
- access/terms under review;
- authorised integration available;
- connected;
- ingestion verified;
- temporarily unavailable;
- disabled.

Seed discovery examples include 1xBet, PariPesa/Paripesa, SportyBet, Bet9ja, BetKing, Betway, Betano, Stake, bet365, William Hill, Pinnacle, Unibet, Bwin, 888sport, DraftKings, FanDuel, BetMGM, Caesars, Betfair, 22Bet, BetWinner, MELbet, MozzartBet, betPawa and MSport. This is a discovery list only—not a statement that each is available in every country, offers every sport, or permits automated access. Add and remove providers through configuration rather than changing analysis code.

## Data access and compliance

Use official APIs, licensed odds/data feeds, or other access methods expressly permitted by the provider's terms and applicable law. Do not bypass logins, bot protections, geographic restrictions, paywalls or other access controls. A provider is not marked live-integrated until the adapter has been tested against live returned data and its market coverage measured. Passing mocked adapter tests verifies parsing and workflow behaviour, not real account access or commercial entitlement.

## Data model

For each provider, event, market and selection, store:
- provider ID and source event ID;
- sport, competition, participants, start time and event status;
- source market ID/name, canonical market family, period/segment, line/handicap and settlement definition;
- every source selection ID/name, participant (if any), odds and odds format;
- market/selection state;
- source timestamp, retrieval timestamp, locale and currency when available;
- adapter version and a safe audit reference to the raw source response.

Keep snapshots over time so price movement, market suspension and historical backtesting can be measured. Never silently discard an unfamiliar market: preserve it as an unclassified source market until its definition is understood.

## Analysis requirements

The analysis pipeline must iterate over the discovered inventory rather than a fixed list:
1. ingest all returned markets and selections for every enabled provider;
2. validate and deduplicate only true equivalent definitions;
3. calculate probabilities only when an appropriate sport/market model and sufficient input data exist;
4. calculate implied probability, bookmaker margin/overround and price comparisons where mathematically valid;
5. show model probability, uncertainty, source odds and timestamp;
6. flag unsupported, unclassified, stale, suspended, missing or unavailable markets explicitly;
7. compare matching options across providers without treating different settlement rules as equivalent.

Never fabricate odds, market availability or model probabilities. "Not enough data" is the correct result when a market cannot be responsibly modelled. No outcome is guaranteed.

## Delivery phases

1. Implement canonical multi-sport event/market/selection schemas and a provider adapter interface.
2. Build the provider registry and market-discovery ingestion so unknown markets are retained.
3. Verify authorised access and actual coverage provider by provider, beginning with 1xBet and PariPesa plus priority operators selected for the target region.
4. Add cross-provider matching, price snapshots and market-family-specific analysis models.
5. Backtest and calibrate each sport and market family independently before publishing confidence/value labels.

## Coverage reporting

The product should report measurable coverage, not vague claims:
- connected providers versus providers in the configured registry;
- events scanned per provider;
- markets and selections discovered per event;
- classified versus unclassified market definitions;
- latest successful collection time and stale-feed warnings;
- analysis-supported versus not-yet-supported options.

"All markets covered" may be displayed only for a provider/event snapshot when the source confirms the full inventory was enumerated successfully. Global completeness across every bookmaker worldwide cannot be guaranteed because provider access, jurisdiction and inventories differ.
