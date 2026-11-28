"""Bookmaker/operator discovery directory.

This is a research directory, not a list of live integrations. Entries are
intentionally marked as not_connected until an authorised integration is tested.
"""
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class BookmakerProfile:
    operator_id: str
    display_name: str
    aliases: tuple[str, ...] = ()
    integration_status: str = "not_connected"
    verification_status: str = "not_verified"
    supported_regions: tuple[str, ...] = ()
    notes: str = "Discovery candidate only; access, terms and regional availability not verified."


# Seed names are discovery candidates, not claims of access or availability.
_SEED_OPERATORS = (
    ("1xbet", "1xBet", ("1xbet",)),
    ("paripesa", "PariPesa / Paripesa", ("parip esa", "paripesa")),
    ("sportybet", "SportyBet", ("sporty bet",)),
    ("bet9ja", "Bet9ja", ()),
    ("betking", "BetKing", ()),
    ("betway", "Betway", ()),
    ("betano", "Betano", ()),
    ("stake", "Stake", ()),
    ("bet365", "bet365", ()),
    ("william-hill", "William Hill", ()),
    ("pinnacle", "Pinnacle", ()),
    ("unibet", "Unibet", ()),
    ("bwin", "Bwin", ()),
    ("888sport", "888sport", ("888 sport",)),
    ("draftkings", "DraftKings", ()),
    ("fanduel", "FanDuel", ()),
    ("betmgm", "BetMGM", ()),
    ("caesars", "Caesars", ()),
    ("betfair", "Betfair", ()),
    ("22bet", "22Bet", ()),
    ("betwinner", "BetWinner", ()),
    ("melbet", "MELbet", ()),
    ("mozzartbet", "MozzartBet", ()),
    ("betpawa", "betPawa", ()),
    ("msport", "MSport", ()),
)


class BookmakerDirectory:
    """In-memory, extensible directory of bookmaker discovery candidates."""

    def __init__(self, profiles: Iterable[BookmakerProfile] | None = None) -> None:
        self._profiles: dict[str, BookmakerProfile] = {}
        for profile in profiles if profiles is not None else self.seed_profiles():
            self.register(profile)

    @staticmethod
    def seed_profiles() -> tuple[BookmakerProfile, ...]:
        return tuple(
            BookmakerProfile(operator_id=operator_id, display_name=name, aliases=aliases)
            for operator_id, name, aliases in _SEED_OPERATORS
        )

    def register(self, profile: BookmakerProfile) -> None:
        operator_id = profile.operator_id.strip().lower()
        if not operator_id:
            raise ValueError("operator_id must be a non-empty stable identifier")
        if operator_id in self._profiles:
            raise ValueError(f"bookmaker already registered: {operator_id}")
        if profile.integration_status not in {
            "not_connected", "access_review", "authorised", "connected",
            "ingestion_verified", "temporarily_unavailable", "disabled",
        }:
            raise ValueError("unsupported integration_status")
        if profile.verification_status not in {
            "not_verified", "partially_verified", "verified", "rejected",
        }:
            raise ValueError("unsupported verification_status")
        self._profiles[operator_id] = BookmakerProfile(
            operator_id=operator_id,
            display_name=profile.display_name.strip(),
            aliases=tuple(a.strip() for a in profile.aliases if a.strip()),
            integration_status=profile.integration_status,
            verification_status=profile.verification_status,
            supported_regions=tuple(r.upper() for r in profile.supported_regions),
            notes=profile.notes,
        )

    def list_profiles(self, query: str | None = None) -> list[dict]:
        profiles = sorted(self._profiles.values(), key=lambda item: item.display_name.casefold())
        if query:
            needle = query.casefold().strip()
            profiles = [
                item for item in profiles
                if needle in item.display_name.casefold()
                or needle in item.operator_id.casefold()
                or any(needle in alias.casefold() for alias in item.aliases)
            ]
        return [asdict(profile) for profile in profiles]

    def get(self, operator_id: str) -> BookmakerProfile:
        try:
            return self._profiles[operator_id.strip().lower()]
        except KeyError as exc:
            raise KeyError(f"bookmaker is not in the discovery directory: {operator_id}") from exc
