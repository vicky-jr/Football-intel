# Football Intel intelligence architecture

## Mission

Football Intel is a multi-sport, multi-bookmaker market-intelligence platform. It studies (1) real-sport bookmaker pricing and sports-event behaviour, and (2) bookmaker-hosted proprietary games such as virtual sports, instant virtuals, crash games, wheels, dice and other game formats. It turns verified observations and published game rules into explainable research and carefully evaluated statistical outputs.

We cannot infer a bookmaker's private source code, risk limits or internal trading algorithm merely from its public odds. We can study observable behaviour, formulate hypotheses and test them against timestamped evidence. Every conclusion must be labelled as an observation, hypothesis or validated finding.

## Architecture

    Authorised data providers
      -> provider adapters and registry
      -> discovery and ingestion orchestrator
      -> raw payload archive and ingestion audit
      -> canonical event / market / selection catalogue
      -> timestamped odds and market-state observation store
      -> feature engineering and research pipelines
      -> statistical validation and model registry
      -> intelligence API and evidence retrieval
      -> conversational assistant and user dashboard

### Provider and coverage service
Owns provider configuration, adapter lifecycle, authentication, entitlement discovery, rate limits, health and coverage reporting. Provider states: discovered, access under review, authorised, connected, ingestion verified, degraded, disabled. An adapter class alone does not mean a provider is integrated.

### Discovery and ingestion service
Enumerates available books, sports, competitions, events and all returned event markets. Supports prematch, in-play, player props and futures only where the source/account provides them. Ingestion is idempotent, respects provider polling guidance and records source time separately from retrieval time. Partial responses, rate limits and failures are visible.

### Canonical market catalogue
Stores original provider IDs and labels beside canonical definitions. Identity should account for sport, event, market family, period/segment, participant, line/handicap, selection and settlement definition. Unknown definitions remain queryable as unclassified records. The 100,000+ target is a scalable catalogue across sports/providers, not a claim that every event has that many options.

### Historical observation service
Stores timestamped odds and state snapshots, market additions/removals, suspensions, reopenings and price changes. Link each observation to provider, event, market, selection, odds format, source timestamp, retrieval timestamp and adapter version. Retention and redistribution must follow data licences.

### Bookmaker behaviour research
Build empirical profiles from observable behaviour. Candidate measures:
- price-change frequency and magnitude by sport, competition and market family;
- time between comparable price moves across monitored books;
- first-observed mover share within a defined observation window;
- follow-on response rates and lag distributions;
- price dispersion and disagreement;
- suspension/reopening frequency where captured;
- opening-to-closing movement and closing-price performance.

A first mover is only first among providers monitored at the relevant sampling cadence. Report coverage, sampling interval, missing observations and uncertainty. Sequence or correlation does not establish causation or access to private algorithms.

### Proprietary bookmaker games intelligence
Treat bookmaker-hosted games as a first-class product domain, separate from real-world sports betting. Maintain a game catalogue with operator, game title, studio/provider where disclosed, game family, version, jurisdiction, published rules, payout table, bet options, round identifiers, result history, timestamps and source provenance.

Classify games by mechanics rather than marketing name:
- virtual sports and scheduled simulated competitions;
- instant virtual matches and rapid-round simulations;
- crash/multiplier games;
- wheel and segment games;
- dice, coin-flip, card and number-draw games;
- slots, table games and other RNG-based formats where research and data access are permitted.

Use a distinct research adapter per game and source. Collect publicly available rules, payout tables, round/result histories and any official fairness-verification material. Where lawful and permitted, record observations from user-provided histories or authorised feeds. Do not automate account access or bypass controls. Store the game version and rules effective at the time of each observation because mechanics can change.

Research methods depend on the game:
- Virtual sports: analyse result frequencies, score distributions, team/participant effects described by the rules, sequence dependence, round cadence and whether historical records are consistent with published mechanics.
- Crash games: analyse multiplier distributions, empirical tail probabilities, round-to-round dependence and disclosed provably-fair verification data when independently verifiable.
- Wheels/dice/number games: compare observed outcome frequencies with the stated probability model and payout table, accounting for configured risk/segment modes.
- Other games: derive a test plan from the official rules and independently documented mechanics before analysis.

A large historical sample can test whether observations are consistent with a stated distribution; it cannot reveal a future random result or prove a hidden algorithm. If a game uses a properly implemented RNG with independent outcomes, past results do not provide a reliable next-result prediction. Distinguish statistical anomalies from evidence of manipulation, and do not allege either without rigorous independent verification. Calculate theoretical return-to-player/house edge only from complete and trustworthy rules and payout information; label assumptions clearly.

### Sports and market behaviour research
Studies event/participant performance and market-specific historical patterns across supported sports. Each sport and market family needs its own definitions, data sufficiency checks, baselines and validation. Do not transfer a football model to basketball or a match-winner model to player props without separate evidence.

### Analytics and model registry
Keep deterministic calculations (implied probability, overround, price movement) distinct from statistical and machine-learning models. Every model version records training window, features, target, supported scope and evaluation results. Use chronological holdouts, leakage checks, calibration and drift monitoring.

### Evidence-grounded conversational assistant
Answers from retrieved, versioned observations, research reports and model outputs. Each answer should state the observation window, sample size, provider/event coverage, timestamps and freshness, whether a statement is descriptive/hypothetical/validated, uncertainty and conflicting evidence. If evidence is insufficient, say so. Never invent odds, coverage, algorithm details or probabilities.

## Core data entities

- Provider, provider entitlement, bookmaker, sport, competition and event.\n- GameStudio, ProprietaryGame, GameVersion, GameRuleset, GameMode and GameRound.\n- GameOutcomeObservation, PayoutTable, RNGVerificationRecord and GameResearchFinding.
- Source event and canonical event with mapping confidence.
- Source market and canonical market definition.
- Source selection and canonical selection definition.
- Append-only OddsObservation and MarketStateObservation.
- RawPayloadReference with access controls and redaction.
- ProviderScan, CoverageSnapshot and ProviderHealthEvent.
- FeatureSnapshot, ResearchFinding and BehaviourProfile.
- ModelVersion, Prediction, EvaluationRun and CalibrationReport.
- EvidenceBundle for traceable assistant answers.

## Bookmaker Behaviour Profile

Segment each profile by sport, competition, market family and observation period. Candidate metrics include monitored coverage/sample size, price-change rate and magnitude, first-observed mover share, follow-on lag, cross-book dispersion, suspensions/reopenings and opening-to-closing movement. Distinguish unavailable data from zero activity. Never call a bookmaker most accurate without a defined target, benchmark, sufficient sample and out-of-sample evaluation.

## Research and validation standards

1. Define hypotheses and metrics before testing where practical.
2. Use chronological train/validation/test splits and avoid look-ahead leakage.
3. Compare against simple baselines.
4. Report sample sizes, missingness, confidence intervals and multiple-testing risks.
5. Evaluate probability calibration and proper scoring rules where applicable.
6. Account for bookmaker margin and different settlement rules.
7. Track performance by sport, competition, market family and time.
8. Preserve failed experiments and negative results.
9. Require review before promoting findings or models to users.

## Proprietary-game research integrity\nNever claim to know a private RNG seed, source code or future result unless a provider publishes a verifiable mechanism and the data genuinely permits verification. Do not present streaks, hot/cold numbers, apparent cycles or small-sample anomalies as winning systems. Clearly separate descriptive statistics, hypothesis tests and independently verified fairness results. Do not recommend chasing losses or escalating stakes.\n\n## Safety, compliance and operations

Use official APIs, licensed feeds or methods expressly permitted by provider terms and law. Do not bypass logins, bot protections, geographic restrictions or paywalls. Keep credentials server-side, redact secrets, enforce least privilege, audit access and respect retention/display/redistribution rights. User-facing insights must avoid guaranteed-win or guaranteed-profit claims and include appropriate uncertainty and responsible-gambling safeguards.
