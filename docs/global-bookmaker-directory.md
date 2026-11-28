# Persistent global bookmaker directory

## Purpose

The directory is the platform's operator discovery ledger. It distinguishes the
existence of a bookmaker or brand from data access, permission to collect data,
regional availability and verified market coverage.

## Persistence

The directory is backed by the same SQLite database path selected by
`FOOTBALL_INTEL_DB_PATH`. In local development, it defaults to
`data/football_intel.sqlite3`. Initial seed entries are inserted only when absent.
An operator's manually reviewed status is therefore not overwritten by default
seed data when the service restarts.

Each record can retain aliases, parent group, official website, permitted access
method, supported region codes, terms-review status, verification evidence URL,
last checked time and operator notes. Unknown fields stay empty rather than being
filled with assumptions.

## API

- `GET /api/v1/bookmakers`: list candidates.
- `GET /api/v1/bookmakers?q=bet`: search name, ID and aliases.
- `GET /api/v1/bookmakers?region=GB`: list only entries with a recorded GB scope.
- `GET /api/v1/bookmakers?integration_status=ingestion_verified`: filter integration state.
- `GET /api/v1/bookmakers?verification_status=verified`: filter evidence state.
- `GET /api/v1/bookmakers/summary`: directory and verification totals.
- `GET /api/v1/bookmakers/{operator_id}`: inspect an operator.
- `GET /api/v1/bookmakers/{operator_id}/sources`: inspect data-provider identities for an operator.

The HTTP API is read-only. Status changes and source-identity verification are not
exposed as unauthenticated public writes. A future authenticated administrative
workflow must record who changed a status, when, and which evidence justified it.

## Important definitions

- `connected` means a connection is configured and can be attempted; it does not
  prove that a useful schedule or market feed has been received.
- `ingestion_verified` requires successful live authorised data retrieval and
  validation. It does not mean every sport, event, market or region is covered.
- `verified` means the stated record is supported by evidence. It must not be
  interpreted as a licence, legal opinion or global availability guarantee.
- Region codes are recorded only after evidence review. An empty region list means
  unknown/not established, not unavailable everywhere.

## Provider-native source identity

One bookmaker can appear in a data-provider feed with a provider-specific ID and
display label. These are represented as separate source-identity links. New links
start as `candidate`; names alone never establish equivalence. A link can become
`verified` only when an HTTP(S) evidence reference and last-checked timestamp are
recorded. Rejected links remain available for audit and are not used as verified
identity matches.

This keeps source IDs stable for ingestion while allowing display names and
aliases to vary across regions or providers. A verified identity link does not
prove that all the bookmaker's sports or markets are covered.

## Next layer

The next step is a source entitlement and capability matrix: each data feed should
declare what sports, regions, event types, market families, game products and
prematch/live packages it actually returns. Coverage must be measured at that
granularity instead of inherited from the bookmaker's name.


## Suggested identity matching

`GET /api/v1/bookmakers/discovery/suggested-links` compares the latest discovered
provider Books inventory with bookmaker display names and aliases. It uses normalized
exact-name matching only. Potential matches remain suggestions, ambiguous names are
flagged, and fuzzy/unmatched names are not silently assigned. Suggestions are not
persisted as source links and are not used in price comparisons until a trusted
review process records and verifies the association.

An optional `provider_id` query parameter narrows suggestions to one source feed.


## Observed bookmaker market coverage

- GET /api/v1/bookmakers/{operator_id}/coverage joins only verified source
  identity links to stored provider market observations.
- Candidate identity links are displayed separately and never counted as confirmed
  bookmaker coverage.
- The report includes source-native book IDs, events, observed markets, selections,
  sports, competitions and the last captured time.
- An observation count is not proof that every market offered by a bookmaker was
  enumerated. Completeness requires a separate feed-level completeness check.


## Observed provider capability matrix

The capability report is generated from stored scan, catalogue, event and market
observations. It is not an entitlement declaration and does not guess what a provider
could supply but has not yet returned.

- `GET /api/v1/capabilities`: compare all providers with recorded observations.
- `GET /api/v1/capabilities?provider_id=sportradar-prematch`: filter to one provider.
- `GET /api/v1/providers/{provider_id}/capabilities`: inspect a single provider.

The report separates scan health, catalogue discovery and observed activity. It shows
sports and competitions, discovered bookmaker catalogue entries, market packages,
source market labels, selection counts, live market states and freshness timestamps.
It explicitly reports regional availability as `not_established` until a separate
evidence-backed regional-access workflow exists, and proprietary-game coverage as
`not_observed` until game feeds are ingested.

A missing observation means `not_observed`, not `unsupported`. A successful scan
does not establish that the provider exposed every market it offers.
