# Full feature-suite status and engineering boundaries

This document maps each proposed product feature to the current implementation and the
remaining work needed before it can be considered production-ready.

## 1. Cross-book event identity

Implemented: a candidate matcher compares sport, participant names, competition and
kickoff time. It handles reversed home/away ordering, provides component scores and
separates matched, review-required, unmatched and rejected candidates.

Remaining: persistent global event IDs, candidate queues, reviewer approval, alias
management, participant IDs, neutral venues, double-headers and sport-specific matching.

## 2. Historical results and settlement rules

Implemented: a result store keeps source attribution, observed timestamps, verification
state and correction lineage. Settlement profiles are persisted with provider, sport,
canonical market, settlement policies, evidence URL and rules version.

Remaining: independently verified official result integrations, authenticated review
workflow, full settlement coverage per region and automated result reconciliation.
The public API stores submitted profiles as unverified and submitted result records as
unverified.

## 3. Odds comparison and margin removal

Implemented: decimal price validation, reciprocal implied probabilities, best quote
selection, complete-outcome overround and proportional no-vig normalisation.

Comparison is blocked when canonical market identity differs, settlement parity is not
attested, or quote freshness is stale/invalid. The complete-outcome flag must be based on
a provider inventory scan, not a guess. No-vig output is a mathematical adjustment, not a
guaranteed true probability.

Remaining: internal linking of market/selection/settlement identities from verified
provider data, quote synchronization, currency and regional rules, line comparison,
Asian line splitting and provider-specific margin methodology.

## 4. Backtesting and model evaluation

Implemented: timezone-aware chronological split, event-start leakage rejection,
multiclass Brier score, log loss, calibration bins and expected calibration error.

Remaining: historical feature snapshots, model versions, reproducible training runs,
walk-forward validation, confidence intervals, subgroup monitoring, drift detection,
market-specific benchmarks and independent holdout datasets. The existing Poisson
endpoint remains an experimental user-input baseline.

## 5. Market intelligence and alerts

Implemented: price movement trigger evaluation, persisted alert rules, alert history
and cooldown deduplication.

Remaining: alert scheduling, provider polling, persisted last-seen checkpoints,
notification delivery (push/email), per-user channels, quiet hours, retry/dead-letter
handling and alert performance metrics.

## 6. Screenshot and bet-slip intelligence

Implemented: optional Tesseract/Pillow screenshot OCR endpoint, input size and pixel
limits, SHA-256 image fingerprinting, in-memory image processing, OCR-token confidence,
conservative line parsing, unparsed-line preservation, combined odds calculation and
mandatory event/market verification flags.

Remaining: host installation and operation of the Tesseract binary/language packs,
image quality checks, multilingual tuning, malware scanning for any future persisted
uploads, explicit consent UX, secure evidence retention, event/market resolution and
bookmaker-specific bet-slip semantics. OCR text is not semantic verification.

## 7. Responsible-gambling and exposure management

Implemented: configurable single-stake, daily-stake, open-exposure and daily-loss limits,
self-exclusion and cooling-off blocks, plus an append-only user-entered ledger.

Remaining: account identity, user-controlled limit changes and lockouts, support links,
break reminders, account-level exposure reconciliation, time-zone-aware daily windows
and jurisdiction-specific legal review. The ledger is not connected to bookmaker APIs.

## 8. Proprietary bookmaker-game research

Implemented: game/version-scoped sample frequencies, observed return-to-player ratio,
published RTP context and SHA-256 seed-commitment consistency check. It deliberately
returns no next-round prediction.

Remaining: authorised catalogue/result ingestion, published payout/rule verification,
provider algorithm/version adapters, statistical goodness-of-fit and independence
tests, sample-size uncertainty intervals and complete provably-fair outcome validation.
A seed commitment check alone does not verify the generated outcome.

## 9. Specialist AI research team

Implemented: a specialist assessment contract that requires independent unique
specialist IDs, evidence IDs and validated findings. It can abstain or surface conflicts.

Remaining: actual sport/market specialists, independently evaluated training data,
model cards, calibrated outputs, tool permissions, prompt-injection resistance,
agent observability and disagreement adjudication. Agreement between agents is not a
calibrated win probability.

## 10. Bookmaker observable behaviour

Implemented: descriptive summaries from supplied comparable-market observation series,
including movement frequency, absolute change, suspension observations, first-observed
mover share and follow-on counts with a sample sufficiency gate.

Remaining: verified synchronized multi-provider feeds, cadence normalization,
robust missing-data treatment, segment profiles by sport/league/market and
confidence intervals. First-observed mover does not mean the bookmaker moved first.

## 11. Confidence and uncertainty

Implemented: transparent weighted evidence-readiness scoring and hard abstention
conditions for stale/unknown source freshness, unverified mapping/rules, insufficient
sample, uncalibrated models and material disagreement.

Remaining: empirically calibrate the score against real outcomes, define sport-specific
minimum samples, display uncertainty intervals and monitor subgroup failure rates.
The score is not a probability of winning.

## 12. Analyst workspace

Implemented: SQLite-backed projects, evidence-linked notes and watchlists.

Remaining: user authentication, tenant isolation, permissions, audit history, export,
deletion, collaboration and a production web/mobile UI. Do not expose this MVP storage
to untrusted multi-user traffic before security controls exist.

## 13. Evidence-grounded assistant

Implemented foundation: specialist assessments and workspace notes retain evidence
identifiers and can abstain where sources are insufficient.

Remaining: document/source retrieval, source freshness checks, grounded answer
generation, citation rendering, numeric verification, contradiction tracking and
continuous factuality evaluation. No conversational AI assistant has been deployed.

## Release rules

- A provider is not called integrated before a real authorised scan succeeds.
- A result is not verified solely because a client submitted it.
- Cross-book comparison requires matching event, market, selection, line, period and
  verified settlement semantics.
- Missing freshness is unknown, not fresh.
- No model output is released without supported data, evaluation and uncertainty.
- An independent RNG game is not described as predictable from previous results.
- No bet is placed and no funds are handled by these services.
