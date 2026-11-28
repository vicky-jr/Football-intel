# Global Bookmaker, Game Catalogue and Data-Scale Architecture

## Purpose

Football Intel must be designed for a very large and continually changing universe of bookmakers, sports, events, markets, proprietary games, game modes, rules, outcomes and observations. A bookmaker may expose hundreds of proprietary games; each game may have multiple versions, modes, configurations and payout structures. Across many operators and jurisdictions, the catalogue and the data generated from it can become extremely large.

Global scale is an architectural objective, not a claim that every bookmaker or game is currently integrated. Coverage must always be reported from verified sources and actual access.

## 1. First-class catalogue hierarchy

Maintain a versioned catalogue with explicit relationships:

- Operator / bookmaker
- Brand, legal entity and jurisdiction (where known)
- Product family and vertical
- Sport, competition, season and event
- Market definition and selection definition
- Proprietary game, game family, mode and variant
- Ruleset, payout table, paytable, configuration and version
- Data provider, source endpoint/feed and access entitlement

Do not identify a game only by its display name. Use stable internal IDs, source-native IDs, operator IDs, jurisdiction, version and effective dates. Similar names do not prove identical mechanics. Preserve source-native terminology alongside canonical classifications.

Each catalogue record should include source provenance, first-seen and last-seen timestamps, effective-from/to dates where known, verification status, supported regions, availability state, terms/data-rights notes, and confidence in classification. Track renamed, retired, suspended, changed and newly discovered products without destroying historical identity.

## 2. Distinguish catalogue definitions from observations

A catalogue definition describes what something is (for example, a game ruleset or a market definition). An observation records what happened or what was offered at a point in time (for example, an odds quote, game result, availability scan or payout-table capture).

Keep these separate. Never overwrite historical observations with the latest value. Store event time, source publication time when available, retrieval time, and ingestion time. Preserve raw source payloads or durable references subject to provider terms and retention rights, alongside normalized records and transformation versions.

## 3. Data architecture for large volumes

Use a layered data architecture rather than one oversized relational database:

1. **Operational store:** transactional records for users, permissions, catalogue metadata, provider configuration and application workflows.
2. **Ingestion/event layer:** durable queues or streams for provider updates, scans, results, price changes and catalogue changes; support retries, dead-letter handling and replay.
3. **Raw data lake/object storage:** immutable or append-only source payloads and large historical files, partitioned by source, domain and date where practical.
4. **Analytical warehouse/lakehouse:** normalized, query-optimised historical observations, features, aggregates and evaluation datasets.
5. **Search/index layer:** fast discovery across bookmakers, games, events, markets, rules and research documents.
6. **Cache layer:** short-lived caching for frequently requested current coverage and market views, with explicit freshness indicators.

Choose concrete technologies only after measuring workload, deployment constraints, provider terms, operational skills and cost. Avoid premature infrastructure complexity.

## 4. Canonical data contracts

Define provider-neutral contracts for operators, products, games, game versions, events, markets, selections, rules, prices, outcomes, source observations and coverage scans.

Every normalized record should retain:
- Internal stable ID and source-native ID
- Provider/operator and jurisdiction context
- Schema and normalization version
- Event/effective timestamp and retrieval timestamp
- Source/provenance reference
- Freshness and verification state
- Quality flags and known limitations

Support unknown and unclassified markets/games. Preserve raw labels and payload references so new classifications can be added later without losing information.

## 5. Discovery and coverage inventory

Build scheduled and on-demand discovery workflows that enumerate what each authorised source actually exposes. Record scan scope, start/end time, pages/cursors, counts, partial completion, rate limits, errors, unavailable regions and last successful scan.

A coverage dashboard must distinguish:
- Verified available
- Seen historically but not currently available
- Temporarily unavailable or suspended
- Not checked recently
- Not supported by the provider
- Access not entitled or not yet verified
- Unknown / unclassified

Never infer global availability from a single feed. Never claim a bookmaker or game is integrated merely because it appears in a planned catalogue.

## 6. Scale, throughput and reliability

Design ingestion for pagination, rate limits, backpressure, bounded concurrency, idempotency, deduplication, retries with backoff, checkpoints and replay. A failed scan must not silently appear complete. Isolate provider failures so one operator cannot stop all ingestion.

Use workload-aware partitioning and indexing. Keep high-volume time-series observations separate from relatively stable catalogue metadata. Establish retention and archival tiers based on data rights, analytical value, legal requirements and cost. Apply compression and aggregation where useful without discarding raw evidence needed for audits.

Instrument ingestion lag, scan completeness, error rates, duplicate rates, source freshness, queue depth, storage growth, query latency and cost per provider/domain.

## 7. Game-specific intelligence

Treat proprietary games as distinct research domains. Capture rules and versions, game modes, published RTP/house edge, payout tables, bet types, limits, settlement definitions and independently verifiable fairness information when lawfully available.

Analyse observable outcomes with methods appropriate to the game and data-generating process. Test sample sizes, independence, serial dependence, distribution fit, tails, change points and possible anomalies. Do not infer hidden RNG seeds or claim that independent random outcomes are predictable from past outcomes. A statistical anomaly is a finding to investigate, not proof of manipulation.

For every game analysis, state which version and ruleset it applies to. A rules or payout change should create a new effective version and trigger reassessment of prior models.

## 8. Cross-bookmaker matching and deduplication

Maintain explicit entity-resolution relationships between the same real-world event or equivalent market across sources. Matching should use multiple attributes and confidence scores, retain source-specific identities, and allow human review for ambiguous cases.

Do not merge markets with different settlement rules, periods, player inclusion rules, void conditions or line definitions merely because their labels look similar. Preserve bookmaker-specific definitions and map them to canonical concepts only when equivalence is justified.

## 9. Research and model data governance

Feature pipelines must be reproducible and time-aware. Historical backtests may use only information that was available at the prediction timestamp. Store feature definitions, source lineage, model versions, training windows, evaluation windows and data snapshots.

Avoid leakage, duplicate-source counting and correlated-model overconfidence. Monitor drift and data quality. When source coverage is weak, stale or incomplete, reduce confidence or abstain rather than filling gaps with invented values.

## 10. Security, privacy and data rights

Use authorised APIs, licensed feeds, public information and user-provided data under applicable terms. Do not bypass authentication, bot controls, geo restrictions, paywalls or provider limits. Track contractual rights, permitted uses, geographic restrictions, attribution requirements and retention limits per source.

Separate user personal data from shared market intelligence. Apply least privilege, encryption, secrets management, audit logging, tenant isolation, data minimisation and deletion/export workflows. Never expose one user's private uploads or betting history to another user.

## 11. Cost and operational controls

At global scale, data collection and retention can become expensive. Prioritise sources and refresh rates according to user value, reliability, freshness needs, legal rights and measured cost. Use adaptive polling: faster for genuinely time-sensitive markets, slower for stable catalogues, and stop or reduce collection when a source is unavailable or not entitled.

Track storage, compute, bandwidth and provider costs by source and feature. Define budgets, quotas, alert thresholds and graceful degradation. Do not promise continuous real-time coverage where the provider only offers periodic updates.

## 12. User-facing transparency

Expose useful coverage and freshness information: source, last checked time, supported region, market/game version, availability state and known limitations. Clearly distinguish live, delayed, historical, estimated and user-supplied data.

The interface should let users explore by bookmaker, sport, game family, game, version, mode, market and jurisdiction. Search and filters must remain usable as the catalogue grows. Provide an explicit "not enough reliable data" result.

## 13. Phased implementation

1. Extend provider-neutral contracts and catalogue IDs/versioning.
2. Implement discovery scans and honest coverage-state reporting.
3. Add durable ingestion jobs, checkpoints, idempotency and failure isolation.
4. Persist raw payload references and normalized observations.
5. Add storage/search/analytics components based on measured needs.
6. Pilot one authorised source and one bounded proprietary-game family.
7. Measure throughput, completeness, freshness, quality and operating cost.
8. Expand source-by-source and game-family-by-game-family only after the pilot is reliable.

## Non-negotiable principles

- Global ambition does not equal current coverage.
- Catalogue definitions and time-stamped observations are different data.
- Preserve provenance, versions and historical changes.
- Unknown data stays unknown; do not fabricate completeness.
- Similar game names do not prove equivalent rules or RNG.
- More data is useful only when its quality, rights, freshness and analytical value are understood.
- Scale incrementally, measure costs, and preserve the ability to replay and audit decisions.
