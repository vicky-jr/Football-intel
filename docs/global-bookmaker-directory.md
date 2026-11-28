# Global bookmaker directory and verification states

## Why this exists

The platform must be able to track bookmakers across countries and regions without
confusing a name in a directory with a working data integration. The directory is a
discovery index; it is not a claim that every listed operator is legally available,
licensed for the user, or accessible through an authorised API.

## Status model

Each operator has independent integration and verification states:

- `not_connected`: discovery candidate only; no working connection is configured.
- `access_review`: terms, data rights, geography or commercial entitlement are being reviewed.
- `authorised`: an allowed access route has been established, but ingestion is not yet verified.
- `connected`: credentials/configuration exist and a connection can be made.
- `ingestion_verified`: live authorised data has been collected and checked.
- `temporarily_unavailable`: a previously working source is currently failing or unavailable.
- `disabled`: deliberately not used.

Verification is separately recorded as `not_verified`, `partially_verified`,
`verified` or `rejected`. A live connection does not automatically mean complete
coverage of every sport, event, market, country or product offered by an operator.

## API

- `GET /api/v1/bookmakers`: list discovery candidates.
- `GET /api/v1/bookmakers?q=bet`: search display names, IDs and aliases.
- `GET /api/v1/bookmakers?integration_status=not_connected`: filter by state.
- `GET /api/v1/bookmakers/{operator_id}`: inspect one operator.

The initial directory is a deliberately small seed list and must grow through
research and authorised integrations. It is not a definitive list of all bookmakers
worldwide. Region lists remain empty until evidence establishes the relevant market
and permitted coverage. Never infer a user's legal eligibility from this directory.

## Expansion rules

1. Give each legal operator/brand a stable internal ID; model parent groups and brands
   separately when evidence warrants it.
2. Store source-specific IDs and regional product variants without collapsing them.
3. Record official access route, terms/data-rights review, jurisdiction, evidence URL,
   last checked time and integration owner before enabling ingestion.
4. Mark `ingestion_verified` only after live authorised responses are validated.
5. Measure coverage separately by operator, jurisdiction, sport, competition, event,
   market family, selection, prematch/live mode and freshness.
6. Keep unsupported, blocked, stale, unknown and untested states explicit.
7. Never bypass authentication, geographic restrictions, bot controls or provider terms.

The goal is worldwide extensibility and honest measurement—not an unsupported claim
of universal access.
