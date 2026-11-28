# Data freshness and provenance

Freshness is assessed separately for the provider's own update timestamp and
the time our collector captured the response.

- `collection_recency` tells us how recently our system observed the payload.
- `source_freshness` tells us how old the provider says the market update is.
- Missing, malformed or timezone-naive source timestamps remain unknown.
- Future timestamps beyond the configured clock-skew tolerance are flagged.
- A recently captured response is not assumed to contain fresh provider data.

The API accepts a configurable maximum age for inspection. Production policies
should be provider- and market-specific and should also consider feed latency,
polling intervals, event start time, market suspension and contractual service
levels. This first version is descriptive; it does not yet automatically block
model inference or user-facing recommendations.
