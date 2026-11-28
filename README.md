# Football Intel

Football Intel is an experimental, bookmaker-agnostic, multi-sport market-analysis and
sports-intelligence platform. It is being developed as a research product, not as a
guaranteed-betting or automated wagering service.

## Product mission

The platform aims to study real sports markets and bookmaker-hosted proprietary games
(virtual sports, crash games, wheels, dice and other formats) using authorised data,
published rules and reproducible analysis. It preserves original source observations,
builds a common market vocabulary, evaluates models chronologically and reports
uncertainty rather than manufacturing confidence.

The system does not claim access to bookmakers' private source code, trading models or
random-number generators. Historical independent random outcomes are not a reliable way
to predict the next independent outcome.

## Current capability foundations

- **Provider-neutral ingestion:** provider registry, bounded async discovery, partial
  failure reporting and timestamped SQLite market snapshots. No live bookmaker feed is
  currently verified or connected.
- **Market identity:** versioned canonical definitions and explicit provider mappings.
  Unknown markets remain unclassified; there are no production bookmaker mappings loaded.
- **Settlement rules:** persistent, versioned rule profiles and semantic comparison.
  Profiles submitted through the API are stored as unverified; official evidence review
  is required before they can support comparisons.
- **Cross-provider events:** candidate matching uses sport, participants, competition
  and kickoff time. Ambiguous matches require review; global event linking is not yet a
  durable approved workflow.
- **Odds research:** decimal odds, reciprocal implied probabilities, best available
  quoted price and proportional no-vig normalisation. Overround is shown only when a
  complete mutually exclusive outcome set is attested.
- **Historical evidence:** event results retain source name, URL, timestamp, verification
  status and correction lineage. User-submitted API results are not marked verified.
- **Market movement and alerts:** historical selection prices, threshold alert rules,
  cooldown deduplication and stored alert events. Push/email/mobile notification delivery
  is not implemented yet.
- **Model evaluation:** chronological leakage checks, multiclass Brier score, log loss
  and expected calibration error. No production-trained or calibrated model is claimed.
- **Bookmaker behaviour:** descriptive summaries of observed price changes, suspensions,
  first-observed mover share and follow-on behaviour, with sample-size gates.
- **Bet-slip intelligence:** reconstructs explicit selection/odds lines from OCR text
  supplied by a caller. It does not currently perform OCR on image bytes.
- **Responsible-gambling controls:** configured single-stake, daily-stake, exposure,
  daily-loss, self-exclusion and cooling-off checks, plus a user-entered risk ledger.
  The ledger is not connected to bookmaker accounts.
- **Proprietary-game laboratory:** sample outcome frequencies, observed payout/stake
  ratios, published RTP context and a SHA-256 seed-commitment consistency check.
  Full game-outcome verification requires each game's published algorithm and inputs.
- **Specialist research interface:** evidence-gated specialist assessments, conflict
  reporting and abstention. Actual specialist AI models/agents have not been deployed.
- **Confidence and analyst workspace:** transparent evidence-readiness scoring, local
  projects, evidence-linked notes and watchlists. Authentication and tenant isolation
  are still required before multi-user public deployment.

See [the complete capability notes](docs/feature-suite.md), [market taxonomy](docs/market-taxonomy.md),
[settlement rules](docs/settlement-rules.md), [data quality](docs/data-quality.md) and
[the development roadmap](docs/development-roadmap.md).

## Running locally

Python 3.11 or 3.12 is exercised in CI.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `/docs` for the interactive API reference. The default SQLite database is
`data/football_intel.sqlite3`. Set `FOOTBALL_INTEL_DB_PATH` to choose another path.
The `data/` directory and SQLite database files are excluded from Git.

## API groups

- `/api/v1/coverage`, `/api/v1/scans`: ingestion coverage and scan history.
- `/api/v1/taxonomy/definitions`: canonical market definitions.
- `/api/v1/settlement-rules`: settlement profiles.
- `/api/v1/events/match`: candidate cross-provider event matching.
- `/api/v1/odds/compare`: comparable quote calculations.
- `/api/v1/models/backtest`: chronological forecast evaluation.
- `/api/v1/alerts`: price alert rules, evaluations and alert history.
- `/api/v1/bet-slips/reconstruct`: reconstruction from supplied OCR text.
- `/api/v1/risk`: configured risk checks and user-entered records.
- `/api/v1/games`: proprietary-game descriptive research.
- `/api/v1/bookmakers/behaviour`: observable behaviour summaries.
- `/api/v1/intelligence`: specialist aggregation and evidence confidence.
- `/api/v1/results`: historical result records.
- `/api/v1/workspaces`: local analyst projects, notes and watchlists.

## Important production limitations

No bookmaker feed or live result provider is currently verified. The first Sportradar
transport is only a thin authenticated HTTP foundation; route availability, entitlements,
regional coverage, terms, storage rights and redistribution rights must be confirmed
before a production adapter is declared integrated.

The API is an engineering MVP and is not production-secure for public multi-user use.
Before deployment it needs authentication, role-based access control, tenant isolation,
secret management, rate limiting, audit trails, privacy/retention controls, backups,
monitoring and security review. Analyst workspace and user-entered risk records are
currently local storage foundations, not secure account services.

A native OCR/image upload service, push notifications, deployed specialist AI models,
an immutable model registry, walk-forward training pipelines, live bookmaker adapters
and production settlement verification remain future integration work. API request
flags and user-provided material are not themselves proof that a source or rule is true.

No guaranteed-win, guaranteed-profit, risk-free or next-RNG-outcome claims are made.
