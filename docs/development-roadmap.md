# Football Intel development roadmap

## Completed foundations

- [x] FastAPI application, experimental user-supplied-statistics analysis and CI.
- [x] Provider-neutral contracts, registry, bounded ingestion and partial failure reports.
- [x] SQLite scan history, event records, raw market snapshots and coverage summaries.
- [x] Historical selection price movement.
- [x] Versioned canonical market vocabulary with conservative explicit mapping.
- [x] Provider-source freshness separated from collection recency.
- [x] Persistent settlement profiles and settlement parity comparison.
- [x] Cross-provider event candidate matching with ambiguity states.
- [x] Historical result records with source provenance and correction lineage.
- [x] Decimal odds, implied probabilities, best price, overround and proportional no-vig.
- [x] Chronological model evaluation with Brier, log loss and calibration error.
- [x] Threshold alerts, persisted alert rules, event history and cooldown deduplication.
- [x] OCR-text bet-slip reconstruction and verification-required output.
- [x] Optional Tesseract/Pillow screenshot OCR endpoint with in-memory image handling.
- [x] Responsible-gambling limit checks and user-entered exposure ledger.
- [x] Proprietary-game sample analysis and seed-commitment consistency check.
- [x] Specialist evidence aggregation and confidence/abstention gate.
- [x] Observable bookmaker behaviour summaries.
- [x] Local analyst projects, evidence-linked notes and watchlists.
- [x] Python 3.11/3.12 automated test suite.

## Next build priorities

### 1. Verified live data
- Verify Sportradar routes, plan entitlement, available bookmakers, market packages,
  regions, polling cadence, historical access and storage/display rights.
- Identify direct bookmaker feeds only where authorised.
- Build one live provider end-to-end with exact coverage and freshness reporting.
- Preserve raw responses, provider timestamps, request IDs, pagination cursors and
  rate-limit information.

### 2. Identity and taxonomy operations
- Persist canonical provider-to-market mapping decisions with reviewer, evidence,
  version and change history.
- Build a global event-link candidate queue and human approval workflow.
- Resolve team/player aliases, competition IDs, neutral venues and event reschedules.
- Compare only fully aligned market/selection definitions and verified settlement rules.

### 3. Historical intelligence and alerts
- Collect synchronized prices, market states, event results and settlement outcomes.
- Add line movement, movement velocity, volatility and suspension/reopening analysis.
- Add scheduled alert polling and push/email delivery with retry and quiet hours.
- Build bookmaker behaviour reports with uncertainty intervals and cadence correction.

### 4. Models and AI research
- Create immutable point-in-time feature snapshots and a versioned model registry.
- Build sport/market-specific baselines and walk-forward evaluation.
- Add probability calibration, subgroup metrics, drift monitoring and independent review.
- Deploy specialist agents only when their data scope and performance are validated.
- Add evidence retrieval, source citations and numeric consistency checks to the assistant.

### 5. Bet-slip and proprietary games
- Add secure image intake and a supported OCR service.
- Implement event/market resolution for parsed slip lines and manual correction.
- Select one permitted proprietary-game pilot with published rules and versioned results.
- Add sample-size aware distribution tests and complete provably-fair verification where
  the provider publishes all required inputs and algorithms.

### 6. Product security and delivery
- Add authentication, RBAC, tenant isolation, secrets management and audit trails.
- Move production data to PostgreSQL with migrations, backups and retention.
- Add monitoring, incident response, API quotas and privacy controls.
- Build the analyst workspace UI and notification preferences.
- Validate legal, age, advertising and responsible-gambling requirements by jurisdiction.

## Release gates

- No live integration claim without a verified successful scan and data-rights review.
- No automatic event link when candidate identity is ambiguous.
- No cross-book price comparison without a canonical market and verified settlement parity.
- No source-fresh claim when provider freshness is unknown.
- No model probability without supported inputs, version, evaluation and uncertainty.
- No assistant claim without traceable source evidence.
- No claims to predict independent random outcomes.
- No guaranteed-win, guaranteed-profit or risk-free language.
