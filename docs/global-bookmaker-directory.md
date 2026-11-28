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

The HTTP API is read-only. Status changes are deliberately not exposed as
unauthenticated public writes. A future authenticated administrative workflow
must record who changed a status, when, and which evidence justified it.

## Important definitions

- `connected` means a connection is configured and can be attempted; it does not
  prove that a useful schedule or market feed has been received.
- `ingestion_verified` requires successful live authorised data retrieval and
  validation. It does not mean every sport, event, market or region is covered.
- `verified` means the stated record is supported by evidence. It must not be
  interpreted as a licence, legal opinion or global availability guarantee.
- Region codes are recorded only after evidence review. An empty region list means
  unknown/not established, not unavailable everywhere.

## Next layer

The next step is a source entitlement and capability matrix: each data feed should
declare what sports, regions, event types, market families, game products and
prematch/live packages it actually returns. Coverage must be measured at that
granularity instead of inherited from the bookmaker's name.
