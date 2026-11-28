# Global Intelligence Decision Engine

## Purpose

The Global Intelligence Decision Engine is the evidence-fusion and decision layer for Football Intel. It serves real-world sports markets and bookmaker-hosted games across every bookmaker, sport, region and game family for which lawful, reliable data access can be established.

Its job is not to collect the largest possible number of opinions. Its job is to consider all relevant available evidence, understand its provenance and quality, combine independent analytical methods appropriately, challenge proposed conclusions, and produce traceable decisions that match the user's request.

## Scope

### Sports and markets
Support football, basketball, tennis, cricket, baseball, hockey, volleyball, esports and additional sports as their data and market definitions become available. Discover all markets and selections returned by each authorised source, including player props, team statistics, fouls, tackles, cards, corners, shots, totals, handicaps, futures and in-play markets where entitled.

### Bookmaker-hosted games
Maintain a separate game domain for virtual sports, instant virtuals, crash/multiplier games, wheels, dice, card/number games, slots and other permitted formats. Research must be specific to the game's actual rules, version, modes, payout table and observable mechanics. Do not assume games with similar branding share an algorithm.

## Evidence and source registry

Every source is registered with:
- source/provider identity and source type;
- bookmaker, operator, sport, game family and jurisdiction coverage;
- access method, licence/terms status and permitted use;
- publication and retrieval timestamps;
- update cadence, latency and known coverage gaps;
- provenance, reliability history and known limitations;
- whether the source is independent of other sources.

Source classes include official bookmaker/provider rules and announcements, licensed sports and odds feeds, official team/league information, historical datasets, scientific papers, reputable reporting, game histories, published payout tables and independently verifiable fairness material.

Do not count copied or syndicated reports as independent corroboration. A source's reliability is assessed for the specific fact it is being used to support; an official lineup source may be authoritative for lineup status but not for a model's probability estimate.

## Model and agent registry

The platform may grow to dozens or hundreds of specialised models and agents. Each registered component must declare:
- task and supported sport, market or game family;
- input features, data requirements and minimum sample criteria;
- model family, version, owner and dependencies;
- training/evaluation windows and leakage controls;
- calibration, discrimination and baseline comparisons;
- out-of-sample results, uncertainty and known failure modes;
- operational cost, latency and last health check.

Use simple baselines before complex models. Candidate components include statistical probability models, rating systems, Bayesian models, tree ensembles, neural networks, time-series models, market-implied probability models, anomaly/change-point detection, distribution and dependence tests, computer vision/OCR, language models and retrieval systems.

AI agents may research, interpret, coordinate specialist tools, identify missing evidence, generate hypotheses and challenge conclusions. They must cite retrieved evidence and structured tool outputs. An LLM's unsupported intuition is not a probability model and must never be treated as independent statistical confirmation.

## Decision pipeline

1. **Interpret request:** Resolve sport/game, date window, bookmaker scope, market restrictions, odds target, stake/combination intent and other explicit constraints. Ask one concise clarification when a required constraint is ambiguous.
2. **Discover coverage:** Query the authorised sources and enumerate all markets/results actually returned. Record what was not accessible or not covered.
3. **Build evidence bundle:** Gather current and historical observations, official information, source metadata, relevant research and game rules. Preserve source and retrieval timestamps.
4. **Select specialists:** Run only models and agents appropriate to the sport, market, game mechanic and available data.
5. **Generate candidates:** Produce estimates with model version, inputs, sample size, freshness and uncertainty. Keep market-implied probabilities and model estimates distinct.
6. **Challenge candidates:** Run data-quality checks, settlement-definition checks, calibration checks, chronological backtests, sensitivity tests, correlation checks and a contrarian/falsification review.
7. **Fuse evidence:** Combine calibrated, sufficiently independent signals. Account for correlated models and duplicate sources; avoid double-counting evidence. Weight sources and models by task-specific reliability and measured out-of-sample performance, not by popularity or raw count.
8. **Apply user objective:** Rank by estimated confidence when no odds target is specified. If the user requests minimum odds or a target combined price, search for combinations satisfying the explicit constraint while reporting the resulting risk and trade-offs. If a specific market category is requested, do not introduce other categories.
9. **Return decision:** Explain the strongest candidates, alternatives, estimated probability where defensible, available price, data freshness, evidence supporting and opposing the conclusion, uncertainty, and why other candidates were rejected. If no candidate meets the requirements, say so.
10. **Track outcomes:** Store recommendations, prices, timestamps, settlement results and model versions for prospective evaluation and continuous improvement.

## Confidence and odds objectives

"Highest confidence" means the strongest evidence-backed estimated probability among the candidates actually analysed; it does not mean certainty, guaranteed success or necessarily positive expected value.

"Best odds" and "minimum combined odds" are separate objectives. A high combined price usually implies greater risk. For combinations, estimate joint probability with dependence accounted for where possible; never multiply individual probabilities as if selections were independent when they are not. Compare expected value only after accounting for bookmaker margin, price availability and settlement rules.

A market category filter (for example, fouls only) is a hard constraint. An odds target is a separate constraint. Do not silently relax either one.

## Proprietary-game inference limits

For virtual and RNG-based games, analyse published rules, game versions, outcome distributions, payout structures, empirical frequencies, independence/serial dependence, tail behaviour and fairness proofs only when the provider exposes data that can be independently checked.

A historical sample can test consistency with a proposed distribution; it cannot reveal private source code, hidden RNG seeds or the next independent random outcome. Do not claim to know when a crash game will reach a multiplier or when a particular result is due. Present empirical probabilities with sample size and uncertainty, and distinguish anomalies from proof of manipulation.

## Validation and release gates

- Every conclusion has traceable evidence and timestamps.
- Coverage claims are limited to providers, events and markets actually enumerated.
- Model estimates are calibrated and tested on chronological unseen data before promotion.
- Baselines, negative results, multiple-testing risks and drift are recorded.
- Cross-book prices are compared only when selection and settlement definitions match.
- Model ensembles account for dependence and duplicated information.
- AI-generated claims are checked against retrieved sources and structured data.
- Unsupported or stale evidence leads to an explicit uncertainty warning or abstention.
- No prediction is described as guaranteed or risk-free.

## Commercial and responsible-use requirements

Potential profitability must be assessed through prospective tracking and realistic backtests that include bookmaker margin, price movement, voids, limits, fees where applicable, variance and drawdown. Historical returns do not guarantee future returns. The product must not encourage chasing losses or escalating stakes.

Use only authorised APIs, licensed feeds, public information and collection methods permitted by applicable law and provider terms. Do not bypass authentication, bot protections, geographic restrictions or paywalls. Protect credentials and respect data retention, display and redistribution rights.

## Initial implementation order

1. Finish reliable provider-neutral ingestion and timestamped storage.
2. Add evidence/source provenance and coverage snapshots.
3. Add canonical market and selection matching with settlement rules.
4. Add model registry, prediction records and evaluation reports.
5. Implement a deterministic decision pipeline before adding complex autonomous agents.
6. Add AI research/contrarian agents with evidence-grounded outputs.
7. Add sports market decisioning and combination optimisation.
8. Add the separate proprietary-game catalogue and game-specific pilot research.
9. Expand providers, sports, game families and model library as verified data access and measurable performance justify.
