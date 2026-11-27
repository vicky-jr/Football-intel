# Bookmaker coverage strategy

## Product requirement

Football Intel is bookmaker-agnostic. It must not be designed around Football.com or any single sportsbook. For a selected fixture, the goal is to discover and analyse every market and selection exposed by each connected/verified bookmaker, then compare equivalent selections across bookmakers.

"Every market" means the complete set actually returned for that event, at the time captured. It does not mean assuming that every operator offers identical markets, or claiming coverage where an operator's feed or page has not been verified.

## Initial Nigeria-focused bookmaker watchlist

The first discovery and integration queue should include:

- SportyBet
- Bet9ja
- BetKing
- 1xBet
- MSport
- Betway
- Betano
- iLOTBET
- Stake
- BC.Game
- PariPesa / Paripesa
- MozzartBet
- 22Bet
- BetWinner
- MELbet
- betPawa
- NairaBET
- MerryBet
- AccessBET
- Surebet247
- BetBonanza
- LiveScore Bet

This is a starting watchlist, not a claim that every operator is currently accessible, licensed in every Nigerian state, or technically integrable. Confirm each operator's current jurisdictional availability and data-access terms before enabling it.

## Coverage model

Each bookmaker must have an independent adapter. An adapter may use an authorised API, licensed odds/data provider, or another method expressly permitted by the operator's terms. Do not bypass authentication, bot controls, paywalls, or other access restrictions.

For each fixture and bookmaker, store:
- bookmaker identifier and source event identifier
- sport, competition, teams, kickoff time and event status
- market identifier, market name, period/segment and market status
- every selection identifier, selection name, line/handicap and decimal odds
- source timestamp, retrieval timestamp, currency/locale if relevant
- raw source payload or a safe audit reference, plus parser/schema version

Normalise names for cross-bookmaker comparison, but preserve the original source labels and identifiers. Never merge two markets merely because their display names look similar; period, line, settlement rules and participant scope must match.

## Analysis requirements

The analysis pipeline should process the full discovered market catalogue, not a hard-coded shortlist. It should:
1. enumerate all markets and selections returned by each adapter;
2. map equivalent selections only when their settlement definitions match;
3. calculate probabilities only where the model has suitable inputs;
4. compare model probability with bookmaker odds and show implied probability, margin/overround and estimated value with uncertainty;
5. mark unsupported, suspended, missing or stale markets explicitly;
6. retain per-bookmaker timestamps so users can see whether prices are current.

A market must never receive a fabricated probability. If there is insufficient data (for example, a player prop without verified player minutes/lineup context), show "not enough data" rather than a guess.

## Delivery phases

1. Build the provider-neutral event/market/selection schema and adapter interface.
2. Verify data access and coverage for the highest-priority operators.
3. Integrate adapters one at a time and measure actual event/market coverage.
4. Add cross-bookmaker comparison and model support by market family.
5. Backtest each market family separately before displaying calibrated confidence.

## Evidence and scope

The initial Nigeria watchlist is informed by current 2026 bookmaker directories and comparisons. Those third-party lists are discovery inputs only; operator availability, licensing and market inventory must be checked directly before an integration is marked live.

- https://www.goal.com/en-ng/betting/best-betting-sites-in-nigeria/blt84b047d22962ba7b
- https://betloy.com/blog/the-21-best-betting-sites-in-nigeria-for-2026-a-complete-directory-of-every-bookmaker-nigerian-punters-should-know
- https://www.bettingtop10.ng/football/
