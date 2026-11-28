# Settlement-rule profiles

## Why they matter

Markets that look identical can settle differently across operators. Examples
include whether overtime counts, how abandoned or postponed events are treated,
how dead heats are paid, whether pushes return stakes, and what happens after a
player retires.

## Policy

- Store rule profiles per provider, sport, canonical market type and rules version.
- Preserve the provider's evidence URL, region and verification timestamp.
- A profile is not considered verified without an HTTPS evidence reference, a
  timezone-aware verification time and explicit policy values.
- Unknown or operator-specific policy fields prevent a profile from being
  represented as fully verified.
- Cross-provider market comparison is allowed only when both profiles are
  verified and their settlement semantics match.

## Current status

The registry and semantic comparison service are implemented, with no bookmaker
profiles preloaded. This is intentional: provider rules must be checked against
current official rules for the relevant country, product and market before being
treated as verified.
