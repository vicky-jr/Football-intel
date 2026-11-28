# Canonical market taxonomy

## Why it exists

Different bookmakers describe the same market differently. The product therefore
needs an internal market vocabulary before comparing prices. A canonical identity
must preserve sport, settlement period, settlement basis, line and ruleset version.
A market with a different handicap, total line or settlement basis is not the same
market.

## Safe classification policy

- Preserve every source market and selection exactly as received.
- Classify only with an explicit provider mapping based on verified provider data.
- Prefer a stable provider market ID; use a normalized exact name alias only when
  that alias has been deliberately registered.
- Do not use fuzzy text matching to turn unknown markets into known markets.
- Keep unknown or conflicting markets visible as unclassified.
- Treat source period and line as material identity fields.
- Version canonical definitions and provider mappings so historical results can
  be interpreted under the rules that applied at the time.

## Initial catalogue

The first catalogue contains representative football, basketball and tennis market
types. It is not a claim that every provider offers every market. Additional
sports, player props, periods, derivatives and bookmaker-hosted games should be
added as their definitions and settlement rules are verified.

## Current limitations

Provider mappings are intentionally not pre-populated with guessed bookmaker IDs.
No live bookmaker adapter is currently verified. The catalogue and mapping engine
are ready, but cross-book comparisons must remain disabled until authorised source
data and exact market/settlement mappings are available.
