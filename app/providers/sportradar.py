"""Sportradar Odds Comparison v2 Prematch client and provider adapter.

Endpoint paths and pagination follow the current official Odds Comparison v2
API documentation. The adapter does not claim a key has OC Core or any specific
bookmaker coverage; those are determined by the authenticated account response.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date as date_type, timedelta
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.providers.base import ProviderEvent, ProviderMarket, ProviderSelection


PACKAGE_BASES = {
    "prematch": "https://api.sportradar.com/oddscomparison-prematch/",
    "player_props": "https://api.sportradar.com/oddscomparison-player-props/",
    "futures": "https://api.sportradar.com/oddscomparison-futures/",
    "live": "https://api.sportradar.com/oddscomparison-liveodds/",
}


@dataclass(frozen=True)
class FeedMetadata:
    x_origin_id: str | None = None
    max_results: int | None = None
    offset: int | None = None
    result_count: int | None = None
    cache_control: str | None = None
    retry_after: str | None = None


@dataclass(frozen=True)
class FeedResponse:
    payload: dict[str, Any]
    metadata: FeedMetadata


class SportradarOddsClient:
    """Server-side HTTP client for one Odds Comparison v2 package."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 20.0,
        *,
        package: str = "prematch",
        access_level: str | None = None,
        language_code: str = "en",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = api_key or os.getenv("SPORTRADAR_ODDS_API_KEY")
        if not key:
            raise RuntimeError("SPORTRADAR_ODDS_API_KEY is not configured")
        if package not in PACKAGE_BASES:
            raise ValueError(f"unsupported Sportradar package: {package}")
        level = access_level or os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial")
        if level not in {"trial", "production"}:
            raise ValueError("access_level must be 'trial' or 'production'")
        if not language_code.isalpha() or len(language_code) != 2:
            raise ValueError("language_code must be a two-letter code")

        root = base_url or PACKAGE_BASES[package]
        self.package = package
        self.access_level = level
        self.language_code = language_code.lower()
        self._base_url = (
            root.rstrip("/") + f"/{level}/v2/{self.language_code}/"
            if "/v2/" not in root else root.rstrip("/") + "/"
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"x-api-key": key, "accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    @staticmethod
    def _metadata(headers: httpx.Headers) -> FeedMetadata:
        def integer(name: str) -> int | None:
            try:
                value = headers.get(name)
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None
        return FeedMetadata(
            x_origin_id=headers.get("x-origin-id"),
            max_results=integer("x-max-results"),
            offset=integer("x-offset"),
            result_count=integer("x-result"),
            cache_control=headers.get("cache-control"),
            retry_after=headers.get("retry-after"),
        )

    async def get_feed_response(
        self, feed_path: str, params: dict[str, Any] | None = None
    ) -> FeedResponse:
        """Fetch a relative, documented feed and retain pagination/access headers."""
        parsed = urlsplit(feed_path)
        segments = parsed.path.split("/")
        if (
            parsed.scheme or parsed.netloc or parsed.path.startswith("//")
            or any(segment == ".." for segment in segments)
            or not parsed.path or parsed.path.startswith("/")
        ):
            raise ValueError("feed_path must be a safe relative path under the configured API base URL")
        response = await self._client.get(feed_path, params=params)
        # Sportradar documents 403 authentication errors as HTML, not JSON.
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Sportradar returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object from the odds provider")
        return FeedResponse(payload=payload, metadata=self._metadata(response.headers))

    async def get_feed(
        self, feed_path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return (await self.get_feed_response(feed_path, params)).payload

    async def list_all(
        self,
        feed_path: str,
        collection_key: str,
        *,
        page_size: int = 50,
        params: dict[str, Any] | None = None,
        max_pages: int = 1000,
    ) -> list[dict[str, Any]]:
        """Exhaust an offset-paginated feed using response headers when available."""
        if not 1 <= page_size <= 50:
            raise ValueError("Sportradar page_size must be between 1 and 50")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")
        base_params = dict(params or {})
        items: list[dict[str, Any]] = []
        start = int(base_params.pop("start", 0))
        for _ in range(max_pages):
            page_params = {**base_params, "start": start, "limit": page_size}
            response = await self.get_feed_response(feed_path, page_params)
            batch = response.payload.get(collection_key)
            if not isinstance(batch, list):
                raise ValueError(f"Sportradar response is missing list field '{collection_key}'")
            items.extend(item for item in batch if isinstance(item, dict))
            received = response.metadata.result_count
            if received is None:
                received = len(batch)
            if received <= 0:
                break
            if response.metadata.max_results is not None:
                if start + received >= response.metadata.max_results:
                    break
            elif received < page_size:
                break
            start += received
        else:
            raise RuntimeError(f"pagination exceeded safety limit of {max_pages} pages")
        return items

    async def close(self) -> None:
        await self._client.aclose()


class SportradarPrematchProvider:
    """OddsProvider adapter that retains every returned bookmaker market instance."""

    provider_id = "sportradar-prematch"

    def __init__(
        self,
        client: SportradarOddsClient | None = None,
        *,
        api_key: str | None = None,
        access_level: str | None = None,
        page_size: int = 50,
    ) -> None:
        self.client = client or SportradarOddsClient(
            api_key=api_key, package="prematch", access_level=access_level
        )
        if not 1 <= page_size <= 50:
            raise ValueError("page_size must be between 1 and 50")
        self.page_size = page_size
        self._sport_names: dict[str, str] = {}
        self._competition_names: dict[str, str] = {}
        self._competition_sports: dict[str, str] = {}
        self._stage_names: dict[str, str] = {}
        self._schedule_cache: dict[tuple[str, str], list[ProviderEvent]] = {}
        self._books_cache: list[dict[str, Any]] | None = None
        self._sports_cache: list[dict[str, Any]] | None = None
        self.access_tier: str | None = None
        self.access_origin_id: str | None = None

    @property
    def configured_book_count(self) -> int | None:
        """Number of bookmaker records returned by the current authenticated Books feed."""
        return len(self._books_cache) if self._books_cache is not None else None

    async def list_books(self) -> list[dict[str, Any]]:
        if self._books_cache is None:
            feed = await self.client.get_feed_response("books.json")
            payload = feed.payload
            self.access_origin_id = feed.metadata.x_origin_id
            self.access_tier = {
                "MARKET_ORIGIN_CORE_CRAWLERS": "oc_core",
                "MARKET_ORIGIN_MAGIC_CRAWLERS": "oc_us",
            }.get(self.access_origin_id, "unknown")
            books = payload.get("books")
            if not isinstance(books, list):
                raise ValueError("Sportradar Books feed did not contain a books list")
            self._books_cache = [item for item in books if isinstance(item, dict)]
        return list(self._books_cache)

    async def list_sports(self) -> list[dict[str, Any]]:
        if self._sports_cache is None:
            payload = await self.client.get_feed("sports.json")
            sports = payload.get("sports")
            if not isinstance(sports, list):
                raise ValueError("Sportradar Sports feed did not contain a sports list")
            self._sports_cache = [item for item in sports if isinstance(item, dict)]
            self._sport_names = {
                str(item["id"]): str(item.get("name", item["id"]))
                for item in self._sports_cache if item.get("id")
            }
        return list(self._sports_cache)

    async def list_competitions(self, sport_id: str) -> list[dict[str, Any]]:
        path = f"sports/{sport_id}/competitions.json"
        payload = await self.client.get_feed(path)
        competitions = payload.get("competitions")
        if not isinstance(competitions, list):
            raise ValueError("Sportradar Sport Competitions feed did not contain a competitions list")
        result = [item for item in competitions if isinstance(item, dict)]
        for item in result:
            competition_id = item.get("id")
            if competition_id:
                key = str(competition_id)
                self._competition_names[key] = str(item.get("name", key))
                self._competition_sports[key] = sport_id
        return result

    async def list_stages(self, sport_id: str) -> list[dict[str, Any]]:
        """Return active stage/tour records for a stage-structured sport."""
        if sport_id not in self._sport_names:
            raise KeyError(f"sport has not been discovered: {sport_id}")
        payload = await self.client.get_feed(f"sports/{sport_id}/stages.json")
        stages = payload.get("stages")
        if not isinstance(stages, list):
            raise ValueError("Sportradar Sport Stages feed did not contain a stages list")
        result = [item for item in stages if isinstance(item, dict)]
        self._stage_names.update({
            str(item["id"]): str(item.get("description") or item.get("name") or item["id"])
            for item in result if item.get("id")
        })
        return result

    @staticmethod
    def _schedule_entries(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        entries = []
        for row in payload:
            event = row.get("sport_event")
            if isinstance(event, dict):
                entries.append(event)
            elif row.get("id"):
                entries.append(row)
        return entries

    @staticmethod
    def _event_name(event: dict[str, Any]) -> str:
        competitors = event.get("competitors") or []
        home = next(
            (str(item.get("name")) for item in competitors
             if isinstance(item, dict) and item.get("qualifier") == "home"),
            None,
        )
        away = next(
            (str(item.get("name")) for item in competitors
             if isinstance(item, dict) and item.get("qualifier") == "away"),
            None,
        )
        if home and away:
            return f"{home} v {away}"
        return str(event.get("name") or event.get("id") or "Unknown event")

    async def _competition_schedule(self, competition_id: str, scan_date: str) -> list[ProviderEvent]:
        cache_key = (competition_id, scan_date)
        if cache_key in self._schedule_cache:
            return list(self._schedule_cache[cache_key])

        # Competition Schedules is competition-scoped. Filter to the requested
        # UTC date and following date, matching Sportradar's Daily Schedules window.
        rows = await self.client.list_all(
            f"competitions/{competition_id}/schedules.json",
            "schedules",
            page_size=self.page_size,
        )
        start_date = date_type.fromisoformat(scan_date)
        permitted_dates = {start_date.isoformat(), (start_date + timedelta(days=1)).isoformat()}
        sport_id = self._competition_sports.get(competition_id, "")
        sport_name = self._sport_names.get(sport_id, sport_id or "unknown")
        competition_name = self._competition_names.get(competition_id, competition_id)
        events: list[ProviderEvent] = []
        seen: set[str] = set()
        for event in self._schedule_entries(rows):
            event_id = event.get("id")
            if not event_id or str(event_id) in seen:
                continue
            start_time = event.get("start_time")
            if isinstance(start_time, str) and len(start_time) >= 10:
                if start_time[:10] not in permitted_dates:
                    continue
            elif not start_time:
                continue
            seen.add(str(event_id))
            events.append(
                ProviderEvent(
                    provider=self.provider_id,
                    source_event_id=str(event_id),
                    sport=sport_name,
                    competition=competition_name,
                    name=self._event_name(event),
                    start_time=start_time,
                    status=event.get("status"),
                    raw={"sport_event": event, "source": "sportradar_odds_comparison_prematch"},
                )
            )
        self._schedule_cache[cache_key] = events
        return list(events)

    async def list_events(self, competition_id: str, date: str) -> list[ProviderEvent]:
        # Validate date before requesting the provider.
        date_type.fromisoformat(date)
        if competition_id not in self._competition_sports:
            raise KeyError(f"competition has not been discovered: {competition_id}")
        return await self._competition_schedule(competition_id, date)

    @staticmethod
    def _stage_details(event: dict[str, Any]) -> tuple[str | None, str | None, dict[str, Any]]:
        """Extract stage identity when the schedule payload includes sport-event context."""
        context = event.get("sport_event_context") or event.get("context") or {}
        stage = context.get("stage") if isinstance(context, dict) else None
        if not isinstance(stage, dict):
            stage = event.get("stage") if isinstance(event.get("stage"), dict) else {}
        stage_id = stage.get("id") or event.get("stage_id")
        stage_id = str(stage_id) if stage_id is not None else None
        stage_name = stage.get("name") or stage.get("description")
        if not stage_name and stage_id:
            stage_name = None
        return stage_id, str(stage_name) if stage_name else None, stage

    async def list_sport_events(self, sport_id: str, date: str) -> list[ProviderEvent]:
        """Load a daily sport schedule; this is the schedule path for stage-based sports."""
        requested_date = date_type.fromisoformat(date)
        if sport_id not in self._sport_names:
            raise KeyError(f"sport has not been discovered: {sport_id}")

        rows = await self.client.list_all(
            f"sports/{sport_id}/schedules/{requested_date.isoformat()}/schedules.json",
            "schedules",
            page_size=self.page_size,
        )
        permitted_dates = {
            requested_date.isoformat(),
            (requested_date + timedelta(days=1)).isoformat(),
        }
        sport_name = self._sport_names.get(sport_id, sport_id)
        events: list[ProviderEvent] = []
        seen: set[str] = set()
        for row in rows:
            event = row.get("sport_event") if isinstance(row.get("sport_event"), dict) else row
            if not isinstance(event, dict):
                continue
            event_id = event.get("id")
            if not event_id or str(event_id) in seen:
                continue
            start_time = event.get("start_time")
            if not isinstance(start_time, str) or len(start_time) < 10:
                continue
            if start_time[:10] not in permitted_dates:
                continue

            stage_id, stage_name, stage_details = self._stage_details(event)
            if stage_id and not stage_name:
                stage_name = self._stage_names.get(stage_id)
            seen.add(str(event_id))
            events.append(
                ProviderEvent(
                    provider=self.provider_id,
                    source_event_id=str(event_id),
                    sport=sport_name,
                    competition=stage_name,
                    name=self._event_name(event),
                    start_time=start_time,
                    status=event.get("status"),
                    raw={
                        "schedule": row,
                        "sport_event": event,
                        "source": "sportradar_odds_comparison_prematch_daily_schedule",
                        "stage_id": stage_id,
                        "stage": stage_details,
                    },
                )
            )
        return events

    @staticmethod
    def _decimal_odds(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        return result if result > 1 else None

    async def get_event_markets(
        self, event: ProviderEvent, package: str = "prematch"
    ) -> list[ProviderMarket]:
        if package not in {"default", "prematch"}:
            raise ValueError("SportradarPrematchProvider only supports the prematch package")
        payload = await self.client.get_feed(
            f"sport_events/{event.source_event_id}/sport_event_markets.json"
        )
        markets = payload.get("markets")
        if not isinstance(markets, list):
            raise ValueError("Sportradar Sport Event Markets feed did not contain a markets list")

        result: list[ProviderMarket] = []
        for market in markets:
            if not isinstance(market, dict):
                continue
            market_id = market.get("id")
            books = market.get("books") or []
            for book in books:
                if not isinstance(book, dict):
                    continue
                selections = []
                for outcome in book.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    selections.append(
                        ProviderSelection(
                            source_selection_id=str(outcome["id"]) if outcome.get("id") is not None else None,
                            name=str(outcome.get("type") or outcome.get("name") or "unknown"),
                            odds_decimal=self._decimal_odds(outcome.get("odds_decimal")),
                            participant=outcome.get("competitor_name") or outcome.get("participant"),
                            raw=outcome,
                        )
                    )
                book_removed = bool(book.get("removed"))
                market_removed = bool(market.get("removed"))
                status = (
                    "removed" if book_removed or market_removed
                    else "live" if market.get("is_live") is True
                    else "active"
                )
                result.append(
                    ProviderMarket(
                        provider=self.provider_id,
                        source_event_id=event.source_event_id,
                        source_market_id=str(market_id) if market_id is not None else None,
                        name=str(market.get("name") or market_id or "unknown market"),
                        period=market.get("period") or market.get("match_time"),
                        line=market.get("line") or market.get("handicap"),
                        status=status,
                        selections=selections,
                        source_updated_at=book.get("updated_at"),
                        raw={
                            "market": market,
                            "book": book,
                            "feed_generated_at": payload.get("generated_at"),
                            "external_market_id": book.get("external_market_id"),
                            "external_sport_event_id": book.get("external_sport_event_id"),
                        },
                        classified=False,
                        source_book_id=str(book.get("id")) if book.get("id") is not None else None,
                        source_book_name=str(book.get("name") or "unknown bookmaker"),
                    )
                )
        return result

    async def close(self) -> None:
        await self.client.close()


def provider_from_environment() -> SportradarPrematchProvider:
    """Construct a provider only when a server-side API key is configured."""
    if not os.getenv("SPORTRADAR_ODDS_API_KEY"):
        raise RuntimeError("SPORTRADAR_ODDS_API_KEY is not configured")
    return SportradarPrematchProvider()
