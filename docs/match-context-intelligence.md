# Match Context and Intelligence Research

## Purpose

Football Intel must analyse the full context around an event, not only recent scores, basic team statistics or bookmaker prices. This specification begins with football and is designed to generalise to sport-specific context modules for other sports.

Context signals are inputs to research and decisioning, not automatic reasons to change a prediction. Every signal must be sourced, timestamped, scoped to the event and evaluated for relevance and reliability.

## Context domains

### 1. Referee and officiating intelligence
Where reliable historical records exist, collect:
- appointed referee and assistant/VAR officials, including confirmation time and later changes;
- cards, fouls, penalties, advantage, added time and dismissal rates;
- home/away and competition-specific splits, with sample sizes;
- disciplinary tendencies by match state and relevant team/player context;
- consistency across seasons and changes in competition or officiating guidance.

Do not label a referee as biased from raw home/away averages. Adjust for competition, teams, match tempo, foul opportunities, sample size and selection effects. Separate referee tendencies from causal effects and avoid inferring intent.

### 2. Team tactics and matchup
Represent likely and confirmed formations, pressing intensity, defensive line, possession style, transition threat, set-piece approach, width, build-up patterns, tactical changes, coach tendencies and matchup-specific strengths/weaknesses. Use confirmed lineups when available; otherwise mark lineups and tactical setups as predicted with uncertainty.

### 3. Squad, player and availability
Track injuries, suspensions, fitness, returns, minutes/load, rotation likelihood, transfers, player roles, likely replacements, goalkeeper changes and confirmed starting lineups. Record the source and the time the information became known. Do not treat rumours as confirmed absences.

### 4. News and team environment
Monitor relevant, reputable and preferably primary sources for:
- manager/coach statements and changes;
- player or staff disputes, morale-related reports and dressing-room claims;
- contract, transfer and selection developments;
- club ownership, financial, travel or operational issues;
- disciplinary matters and competition announcements;
- public statements that may affect motivation or preparation.

Use careful language. "Morale" is not directly observable from most news reports. Record the actual reported event, source quality, corroboration and uncertainty; do not turn speculation or social-media rumours into a numeric morale fact.

### 5. Motivation and competition context
Consider table position, title/relegation/promotion races, qualification scenarios, knockout/two-leg aggregate state, rivalry context, tournament format, must-not-lose incentives, rotation incentives and whether a draw is strategically acceptable. Avoid simplistic narratives such as "must win means they will win."

### 6. Schedule, fatigue and travel
Collect rest days, recent minutes, fixture congestion, extra time, travel distance/time zones, altitude transitions, recovery windows, squad depth and schedule asymmetry. Distinguish measured workload from inferred fatigue.

### 7. Venue, weather and playing surface
Where relevant and sourced, consider home/away/neutral venue, pitch dimensions and condition, surface type, altitude, temperature, humidity, wind, precipitation, roof status and forecast uncertainty. Evaluate which markets these factors plausibly affect (for example, passing, aerial play, shot quality or set pieces) rather than applying a generic adjustment.

### 8. Match conditions and external events
Track kickoff changes, postponement risk, crowd restrictions, security conditions, travel disruption, unusual venue arrangements, competition rule changes and other verified developments that can affect preparation or event conditions.

### 9. Historical and situational performance
Analyse team/player performance by opponent style, home/away, rest, competition, game state, formation, venue and other justified contexts. Use adequate sample sizes, shrinkage/regularisation and uncertainty intervals; avoid overfitting tiny splits or treating head-to-head records as inherently predictive.

### 10. Market and bookmaker context
Join contextual features to timestamped odds, line movement, market liquidity/availability where known, price dispersion and bookmaker-specific coverage. Market movement is an observation, not proof of insider information or the reason a price changed.

## Event timeline and evidence provenance

For every event, preserve an as-of timeline:
- event and scheduled kickoff identifiers;
- source publication time, event-effective time and retrieval time;
- when the information first became available to Football Intel;
- source identity, source type, URL/reference and reliability assessment;
- whether information is confirmed, provisional, disputed or a rumour;
- affected teams, players, officials, markets and time window;
- corrections, retractions and later updates.

Predictions must use only information that was available at the prediction timestamp. Historical evaluation must reconstruct this as-of view to prevent look-ahead leakage. Keep original observations and corrections auditable.

## Market-specific impact mapping

Do not assume every context feature affects every market equally. Build and validate explicit feature-to-market hypotheses. Examples:
- referee history may be relevant to cards, fouls and penalties, but only after adjusting for match and competition context;
- likely formations and pressing matchups may influence shots, corners, possession, tackles and goals;
- player role, minutes expectation and opponent style may affect player shots, tackles, passes or fouls;
- weather and pitch conditions may affect passing, crossing, aerial duels and set pieces;
- score-state incentives and aggregate context may affect tempo, cards and late-game tactics.

These are hypotheses to test, not guaranteed effects.

## Context fusion and AI analysis

Specialist agents may summarise official team news, referee records, tactical evidence, schedule/travel factors and weather. A context analyst should:
1. identify relevant context for the specific sport, event and market;
2. retrieve primary sources and corroboration;
3. distinguish facts, reports, inferences and speculation;
4. identify conflicting or stale information;
5. propose feature-to-market hypotheses with evidence;
6. challenge the prediction and state what could invalidate it.

The central decision engine combines context features with statistical model outputs and market information. Do not double-count the same news item repeated across multiple websites. Language-model opinions are not independent evidence and must not replace measured features or calibrated probabilities.

## Validation requirements

- Define the expected direction and affected market before testing where practical.
- Use time-aware data and reconstruct what was known at each prediction timestamp.
- Control for confounders such as competition, team strength, game state and opportunity volume.
- Use chronological out-of-sample evaluation and compare against a baseline without the context feature.
- Measure incremental value, calibration and stability across seasons/competitions.
- Record sample size, missingness, source coverage and uncertainty.
- Retire or down-weight features that fail to add reproducible out-of-sample value.
- Treat multiple hypothesis testing and selective reporting as material risks.

A factor belongs in production decisioning only when its data quality, relevance and incremental value are demonstrated. Collecting more data is useful only when it improves coverage or decisions without adding misleading noise.

## Cross-sport extension

The same framework should support sport-specific context packs. Examples include:
- basketball: player availability, rotations, pace, rest, travel, referee foul patterns and matchup assignments;
- tennis: surface, player fitness, serve/return matchup, schedule, weather and tournament format;
- cricket: pitch, weather, toss, innings format, player availability and ground dimensions;
- baseball: starting pitcher, bullpen workload, batting order, park factors and weather;
- hockey: goalie confirmation, line combinations, special teams, travel and rest.

Each sport requires its own domain definitions, trusted sources, market mappings and validation plan.

## Product and safety requirements

The assistant must communicate what is confirmed, what is uncertain and what is merely a hypothesis. It must not fabricate injuries, referee statistics, quotes, tactics or news. If current information cannot be verified, it must say so. No context factor guarantees an outcome, and no prediction should be presented as certain or risk-free.
