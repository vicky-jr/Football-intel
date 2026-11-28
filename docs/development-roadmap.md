# Football Intel development roadmap

## Scope

The target is both bookmaker behaviour intelligence and sports/market behaviour intelligence, across all sports, providers and market types that can be lawfully and reliably accessed. Football is the first implementation vertical to keep delivery manageable; the architecture remains sport-neutral from day one.

## Phase 0 — Foundation and architecture (current)

- [x] FastAPI foundation and experimental match-analysis endpoint.
- [x] Provider-neutral event/market/selection contracts.
- [x] Provider registry and loss-aware in-memory market inventory.
- [x] Global multi-sport/provider discovery requirements.
- [x] Intelligence architecture and phased roadmap documented.
- [ ] Run the existing test suite in a reproducible environment.
- [ ] Decide database and migration strategy.

Exit: architecture documented, tests run, persistence decision recorded.

## Phase 1 — Reliable ingestion and historical snapshots

- Implement an ingestion orchestrator over the existing provider protocol, registry and inventory.
- Discover provider books, sports, competitions and events.
- Enumerate every market and selection returned for each event and entitled package.
- Persist raw payload references, normalized records and timestamped odds/state observations.
- Record partial scans, failures, rate limits, staleness and provider health.
- Add idempotency, bounded retries and provider-respecting polling.
- Add mock-provider tests for pagination, partial failure, duplicate delivery, unknown markets and state changes.

Exit: a mock provider scans end-to-end; every returned market/selection survives ingestion; snapshots and coverage are queryable; failures are visible.

## Phase 2 — First authorised live data source

- Confirm commercial access, API key, region, book list, sports, competitions and package entitlements.
- Evaluate the planned Sportradar Odds Comparison v2 source, but verify current API routes and account entitlements before coding endpoint assumptions.
- Verify one sport, competition and selected events end-to-end before expanding.
- Measure whether 1xBet and PariPesa/Paripesa are actually included; add direct authorised adapters only where permitted and needed.
- Confirm polling limits, update cadence, historical access, storage rights and end-user display/redistribution rights.

Exit: at least one live integration is tested against real responses and its exact coverage/limitations are reported.

## Phase 3 — Market normalization and cross-book matching

- Build a versioned canonical taxonomy while retaining source labels and settlement rules.
- Match events across providers with confidence scores and manual review for ambiguity.
- Compare selections only when sport, event, participant, period, line, selection and settlement terms align.
- Add odds conversion, implied probability, overround and comparable-price calculations.
- Preserve unknown definitions and provide a classification workflow.

Exit: comparisons contain only genuinely comparable prices and explain unmatched items.

## Phase 4 — Market movement intelligence

- Calculate price deltas, percentage changes, line movement, movement velocity, volatility and suspension/reopening transitions.
- Compare synchronized observations while accounting for provider cadence and missing data.
- Detect unusual movement using transparent thresholds and baselines.
- Build event timelines and alerts with source timestamps and freshness.
- Keep observed movement separate from causal explanations.

Exit: users can inspect a sourced timeline and reproduce every calculation from stored observations.

## Phase 5 — Bookmaker behaviour profiles

- Build profiles segmented by sport, competition and market family.
- Measure first-observed mover share, follow-on rates/lags, price-change frequency/magnitude, dispersion and suspension behaviour.
- State monitored providers, cadence, sample size, uncertainty and missingness.
- Describe observable behaviour only; do not claim proprietary algorithm reverse-engineering.
- Evaluate closing prices against outcomes and baselines where valid.

Exit: each profile metric has a documented definition, data sufficiency rule and reproducible calculation.

## Phase 6 — Sports/market research and predictive models

- Establish sport-specific event, participant and outcome datasets.
- Build simple baselines before machine learning.
- Add market-family-specific models only when data and sample sizes justify them.
- Use chronological holdouts, leakage checks, calibration and appropriate market-specific benchmarks.
- Track model versions, drift, subgroup performance and negative results.
- Keep unsupported markets visible but marked not modelled.

Exit: every user-facing model has a model card, evaluation report and defined supported scope.

## Phase 7 — Evidence-grounded AI research assistant

- Retrieve observations, bookmaker profiles, market timelines and evaluation reports.
- Require answers to show evidence IDs, dates, sample sizes and freshness.
- Separate facts, hypotheses and validated findings.
- Support insufficient-evidence and conflicting-evidence answers.
- Evaluate factual faithfulness and numeric consistency against the database.
- Prevent invented odds, provider coverage, proprietary algorithm details or unsupported probabilities.

Exit: answers are traceable to stored evidence and abstain when data is missing.

## Phase 8 — Multi-sport expansion and product hardening

- Add sports one at a time based on data access, demand and research readiness.
- Validate each sport's event model, market taxonomy and settlement conventions.
- Expand provider coverage region by region, including Nigeria/Africa and international operators where authorised.
- Add mobile-friendly dashboard, alerts, accounts, access controls, monitoring, backups and incident response.
- Review local legal, licensing, age, advertising and responsible-gambling requirements before public launch.

Exit: each added sport/provider has verified coverage, monitoring and documented limitations.

## Release gates

- No live integration claim without a successful verified scan.
- No complete-inventory claim unless the source confirms enumeration for that event snapshot.
- No movement claim without source and retrieval timestamps.
- No bookmaker-behaviour claim without monitored set, time window and sample size.
- No model probability without supported model, inputs, version and uncertainty.
- No cross-book comparison across different settlement definitions.
- No user-facing finding without reproducible calculations and review.
- No guaranteed-win, guaranteed-profit or risk-free language.

## Immediate next engineering task

Implement the Phase 1 ingestion orchestrator and mock-provider tests using the existing provider protocol, ProviderRegistry and MarketInventory. Keep work on feat/football-intel-foundation. Do not connect a live provider until current API routes, account entitlements and data rights are confirmed.
