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
- **Bet-slip intelligence:** includes an optional Tesseract/Pillow screenshot OCR endpoint and
  a text parser that preserves unparsed lines. It requires the Tesseract system executable;
  images are processed in memory and not retained by the endpoint.
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

Open `/docs` for the interactive API reference. Screenshot OCR uses Pillow and pytesseract,
  and also requires the Tesseract executable and suitable language data to be installed on the host.
  The default SQLite database is
`data/football_intel.sqlite3`. Set `FOOTBALL_INTEL_DB_PATH` to choose another path.
The `data/` directory and SQLite database files are excluded from Git.

## First authorised Sportradar scan

The Prematch adapter follows the documented Odds Comparison v2 feeds. It runs only when
a server-side API key is configured. Credentials are never stored in Git.

```bash
export SPORTRADAR_ODDS_API_KEY="your-server-side-key"
export SPORTRADAR_ACCESS_LEVEL="trial"
python scripts/collect_sportradar_prematch.py 2026-11-28
```

Use `production` only when the account is provisioned for production. The scan reports
the `X-Origin-Id` access tier and bookmaker count returned by that key. An `oc_us`
response is not global-core access; OC Core must be enabled by Sportradar Support.
The script stores event and bookmaker-specific market snapshots in local SQLite.

## API groups

- `/api/v1/coverage`, `/api/v1/scans`: ingestion coverage and scan history.
- `/api/v1/integrations/sportradar/status`: local credential configuration status (no provider call).
- `/api/v1/taxonomy/definitions`: canonical market definitions.
- `/api/v1/settlement-rules`: settlement profiles.
- `/api/v1/events/match`: candidate cross-provider event matching.
- `/api/v1/odds/compare`: comparable quote calculations.
- `/api/v1/models/backtest`: chronological forecast evaluation.
- `/api/v1/alerts`: persistent price alert rules, cooldown evaluation, enable/disable and alert history.
- `/api/v1/bet-slips/ocr`, `/api/v1/bet-slips/reconstruct`: screenshot OCR and supplied-text reconstruction.
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

Push notifications, deployed specialist AI models,
an immutable model registry, walk-forward training pipelines, live bookmaker adapters
and production settlement verification remain future integration work. API request
flags and user-provided material are not themselves proof that a source or rule is true.

No guaranteed-win, guaranteed-profit, risk-free or next-RNG-outcome claims are made.
