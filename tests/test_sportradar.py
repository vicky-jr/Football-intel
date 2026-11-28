import asyncio
import httpx
import pytest

from app.providers.base import ProviderEvent
from app.providers.sportradar import SportradarOddsClient, SportradarPrematchProvider
from app.providers.registry import ProviderRegistry
from app.services.ingestion import IngestionOrchestrator
from app.services.market_inventory import MarketInventory
from app.services.sqlite_store import SQLiteMarketStore
from app.providers.registry import ProviderRegistry
from app.services.ingestion import IngestionOrchestrator
from app.services.market_inventory import MarketInventory
from app.services.sqlite_store import SQLiteMarketStore


def _response(payload, headers=None, status=200):
    return httpx.Response(status, json=payload, headers=headers or {})


def test_client_builds_official_v2_url_and_keeps_access_and_pagination_headers():
    seen = {}
    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        return _response({"books":[{"id":"sr:book:1","name":"Demo"}]},
            {"x-origin-id":"MARKET_ORIGIN_CORE_CRAWLERS","x-max-results":"1","x-offset":"0","x-result":"1"})
    async def run():
        client = SportradarOddsClient(api_key="test-key",transport=httpx.MockTransport(handler))
        result = await client.get_feed_response("books.json")
        await client.close()
        return result
    result=asyncio.run(run())
    assert seen["url"]=="https://api.sportradar.com/oddscomparison-prematch/trial/v2/en/books.json"
    assert seen["key"]=="test-key"
    assert result.metadata.x_origin_id=="MARKET_ORIGIN_CORE_CRAWLERS"
    assert result.metadata.max_results==1 and result.metadata.result_count==1


def test_client_refuses_unsafe_relative_paths():
    client=SportradarOddsClient(api_key="test-key",transport=httpx.MockTransport(lambda r:_response({})))
    async def run():
        try:
            with pytest.raises(ValueError): await client.get_feed("../secret.json")
            with pytest.raises(ValueError): await client.get_feed("https://evil.example/feed")
        finally:
            await client.close()
    asyncio.run(run())


def test_client_requires_credentials_and_valid_package():
    with pytest.raises(RuntimeError,match="not configured"):
        SportradarOddsClient(api_key="")
    with pytest.raises(ValueError,match="unsupported"):
        SportradarOddsClient(api_key="test",package="unknown")


def test_list_all_exhausts_pages_using_provider_headers():
    calls=[]
    def handler(request):
        start=int(request.url.params["start"])
        calls.append(start)
        if start==0:
            return _response({"schedules":[{"sport_event":{"id":"one"}}]},
                {"x-max-results":"2","x-offset":"0","x-result":"1"})
        return _response({"schedules":[{"sport_event":{"id":"two"}}]},
            {"x-max-results":"2","x-offset":"1","x-result":"1"})
    async def run():
        client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(handler))
        rows=await client.list_all("competitions/c1/schedules.json","schedules",page_size=1)
        await client.close()
        return rows
    rows=asyncio.run(run())
    assert calls==[0,1]
    assert [x["sport_event"]["id"] for x in rows]==["one","two"]


def test_adapter_discovers_books_sports_and_competitions():
    def handler(request):
        path=request.url.path
        if path.endswith("/books.json"):
            return _response({"books":[{"id":"sr:book:7","name":"Book Seven"}]})
        if path.endswith("/sports.json"):
            return _response({"sports":[{"id":"sr:sport:1","name":"Soccer","type":"competition"}]})
        if path.endswith("/sports/sr:sport:1/competitions.json"):
            return _response({"competitions":[{"id":"sr:competition:17","name":"Premier League","markets":True}]})
        return _response({},status=404)
    async def run():
        client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(handler))
        adapter=SportradarPrematchProvider(client)
        books=await adapter.list_books()
        sports=await adapter.list_sports()
        comps=await adapter.list_competitions("sr:sport:1")
        await adapter.close()
        return books,sports,comps
    books,sports,comps=asyncio.run(run())
    assert books[0]["id"]=="sr:book:7"
    assert sports[0]["id"]=="sr:sport:1"
    assert comps[0]["markets"] is True


def test_adapter_builds_events_from_competition_schedule_and_filters_date():
    def handler(request):
        if request.url.path.endswith("/sports.json"):
            return _response({"sports":[{"id":"sr:sport:1","name":"Soccer","type":"competition"}]})
        if request.url.path.endswith("/sports/sr:sport:1/competitions.json"):
            return _response({"competitions":[{"id":"sr:competition:17","name":"Premier League","markets":True}]})
        if request.url.path.endswith("/schedules.json"):
            return _response({"schedules":[
                {"sport_event":{"id":"e1","start_time":"2026-11-28T13:00:00+00:00",
                  "status":"not_started","competitors":[
                    {"name":"Home FC","qualifier":"home"},{"name":"Away FC","qualifier":"away"}]}},
                {"sport_event":{"id":"e2","start_time":"2026-11-30T13:00:00+00:00","status":"not_started"}}
            ]},{"x-max-results":"2","x-offset":"0","x-result":"2"})
        return _response({},status=404)
    async def run():
        client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(handler))
        adapter=SportradarPrematchProvider(client,page_size=50)
        await adapter.list_sports()
        await adapter.list_competitions("sr:sport:1")
        events=await adapter.list_events("sr:competition:17","2026-11-28")
        await adapter.close()
        return events
    events=asyncio.run(run())
    assert len(events)==1
    assert events[0].name=="Home FC v Away FC"
    assert events[0].competition=="Premier League"


def test_adapter_discovers_stages_and_builds_events_from_daily_sport_schedule():
    seen_paths = []

    def handler(request):
        path = request.url.path
        seen_paths.append(path)
        if path.endswith("/sports.json"):
            return _response({"sports":[{"id":"sr:sport:9","name":"Golf","type":"stage"}]})
        if path.endswith("/sports/sr:sport:9/stages.json"):
            return _response({"stages":[
                {"id":"sr:stage:1","description":"The Open",
                 "scheduled":"2026-11-28T00:00:00+00:00",
                 "scheduled_end":"2026-12-01T00:00:00+00:00"}
            ]})
        if path.endswith("/sports/sr:sport:9/schedules/2026-11-28/schedules.json"):
            return _response({"schedules":[
                {"sport_event":{"id":"event-1","name":"The Open - Round 1",
                  "start_time":"2026-11-28T08:00:00+00:00","status":"not_started",
                  "sport_event_context":{"stage":{"id":"sr:stage:1"}}}},
                {"sport_event":{"id":"event-2","name":"The Open - Round 2",
                  "start_time":"2026-11-29T08:00:00+00:00","status":"not_started",
                  "sport_event_context":{"stage":{"id":"sr:stage:1"}}}},
                {"sport_event":{"id":"event-outside-window","name":"Later Event",
                  "start_time":"2026-11-30T08:00:00+00:00","status":"not_started"}}
            ]},{"x-max-results":"3","x-offset":"0","x-result":"3"})
        return _response({"detail":"unexpected feed"},status=404)

    async def run():
        client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(handler))
        adapter=SportradarPrematchProvider(client)
        try:
            await adapter.list_sports()
            stages=await adapter.list_stages("sr:sport:9")
            events=await adapter.list_sport_events("sr:sport:9","2026-11-28")
            return stages,events
        finally:
            await adapter.close()

    stages,events=asyncio.run(run())
    assert stages[0]["id"]=="sr:stage:1"
    assert len(events)==2
    assert events[0].competition=="The Open"
    assert events[0].raw["stage_id"]=="sr:stage:1"
    assert events[1].source_event_id=="event-2"
    assert any(path.endswith("/sports/sr:sport:9/stages.json") for path in seen_paths)
    assert any(path.endswith("/sports/sr:sport:9/schedules/2026-11-28/schedules.json") for path in seen_paths)


def test_adapter_preserves_book_specific_markets_and_selection_prices():
    def handler(request):
        return _response({"generated_at":"2026-11-28T10:00:00+00:00","markets":[
          {"id":"sr:market:1","name":"1x2","is_live":False,"books":[
            {"id":"sr:book:7","name":"Book Seven","removed":False,"external_market_id":"x1",
             "outcomes":[{"id":"sr:outcome:1","type":"home","odds_decimal":"1.85","open_odds_decimal":"1.9"},
                         {"id":"sr:outcome:2","type":"draw","odds_decimal":"3.4"}]},
            {"id":"sr:book:8","name":"Book Eight","removed":False,
             "outcomes":[{"id":"sr:outcome:1","type":"home","odds_decimal":"1.9"}]}
          ]}
        ]})
    async def run():
        client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(handler))
        adapter=SportradarPrematchProvider(client)
        event=ProviderEvent("sportradar-prematch","sr:sport_event:1","Soccer","Premier League",
           "Home v Away","2026-11-28T18:00:00+00:00","not_started")
        markets=await adapter.get_event_markets(event)
        await adapter.close()
        return markets
    markets=asyncio.run(run())
    assert len(markets)==2
    assert markets[0].source_book_id=="sr:book:7"
    assert markets[0].selections[0].odds_decimal==1.85
    assert markets[0].raw["external_market_id"]=="x1"
    assert markets[1].source_book_id=="sr:book:8"


def test_adapter_rejects_package_other_than_prematch():
    client=SportradarOddsClient(api_key="test",transport=httpx.MockTransport(lambda r:_response({})))
    async def run():
        adapter=SportradarPrematchProvider(client)
        event=ProviderEvent("sportradar-prematch","e","Soccer","League","H v A",None,None)
        with pytest.raises(ValueError,match="only supports"):
            await adapter.get_event_markets(event,"live")
        await adapter.close()
    asyncio.run(run())


def test_full_mock_sportradar_scan_persists_book_specific_prices(tmp_path):
    def handler(request):
        path=request.url.path
        if path.endswith("/books.json"):
            return _response(
                {"books":[{"id":"sr:book:7","name":"Book Seven"}]},
                {"x-origin-id":"MARKET_ORIGIN_CORE_CRAWLERS"},
            )
        if path.endswith("/sports.json"):
            return _response({"sports":[{"id":"sr:sport:1","name":"Soccer","type":"competition"}]})
        if path.endswith("/sports/sr:sport:1/competitions.json"):
            return _response({"competitions":[{"id":"sr:competition:17","name":"Premier League","markets":True}]})
        if path.endswith("/competitions/sr:competition:17/schedules.json"):
            return _response({"schedules":[
                {"sport_event":{"id":"sr:sport_event:77","start_time":"2026-11-28T18:00:00+00:00",
                    "status":"not_started","competitors":[
                        {"name":"Home FC","qualifier":"home"},{"name":"Away FC","qualifier":"away"}]}}
            ]},{"x-max-results":"1","x-offset":"0","x-result":"1"})
        if path.endswith("/sport_events/sr:sport_event:77/sport_event_markets.json"):
            return _response({"generated_at":"2026-11-28T10:00:00+00:00","markets":[
                {"id":"sr:market:1","name":"1x2","is_live":False,"books":[
                    {"id":"sr:book:7","name":"Book Seven","removed":False,
                     "external_market_id":"book-market-1","outcomes":[
                        {"id":"sr:outcome:1","type":"home","odds_decimal":"1.85","open_odds_decimal":"1.90"},
                        {"id":"sr:outcome:2","type":"draw","odds_decimal":"3.40"},
                        {"id":"sr:outcome:3","type":"away","odds_decimal":"4.20"}
                     ]}
                ]}
            ]})
        return _response({"detail":"unexpected feed"},status=404)

    async def run():
        client=SportradarOddsClient(api_key="test-key",transport=httpx.MockTransport(handler))
        provider=SportradarPrematchProvider(client)
        store=SQLiteMarketStore(tmp_path/"sportradar.sqlite3")
        orchestrator=IngestionOrchestrator(
            ProviderRegistry([provider]),MarketInventory(),store=store,max_retries=0
        )
        try:
            report=await orchestrator.scan("sportradar-prematch","2026-11-28",package="prematch")
            return report,store,provider
        finally:
            await provider.close()

    report,store,provider=asyncio.run(run())
    assert report.complete
    assert report.books_discovered==1
    assert report.sports_discovered==1
    assert report.competitions_discovered==1
    assert report.events_discovered==1 and report.events_scanned==1
    assert report.markets_received==1 and report.selections_received==3
    assert provider.access_tier=="oc_core"
    books = store.discovery_inventory(provider="sportradar-prematch", stage="books")
    sports = store.discovery_inventory(provider="sportradar-prematch", stage="sports")
    competitions = store.discovery_inventory(provider="sportradar-prematch", stage="competitions")
    assert books[0]["source_id"] == "sr:book:7"
    assert sports[0]["source_id"] == "sr:sport:1"
    assert competitions[0]["source_id"] == "sr:competition:17"
    snapshots=store.snapshots_for_event("sportradar-prematch","sr:sport_event:77")
    assert len(snapshots)==1
    market=snapshots[0]["markets"][0]
    assert market["source_book_id"]=="sr:book:7"
    assert market["source_book_name"]=="Book Seven"
    assert market["raw"]["external_market_id"]=="book-market-1"
    assert market["selections"][0]["odds_decimal"]==1.85

def test_full_mock_stage_sport_scan_persists_stage_inventory_and_markets(tmp_path):
    def handler(request):
        path = request.url.path
        if path.endswith("/books.json"):
            return _response({"books":[{"id":"sr:book:7","name":"Book Seven"}]})
        if path.endswith("/sports.json"):
            return _response({"sports":[{"id":"sr:sport:9","name":"Golf","type":"stage"}]})
        if path.endswith("/sports/sr:sport:9/stages.json"):
            return _response({"stages":[
                {"id":"sr:stage:1","description":"The Open",
                 "scheduled":"2026-11-28T00:00:00+00:00",
                 "scheduled_end":"2026-12-01T00:00:00+00:00"}
            ]})
        if path.endswith("/sports/sr:sport:9/schedules/2026-11-28/schedules.json"):
            return _response({"schedules":[
                {"sport_event":{"id":"sr:sport_event:99","name":"The Open - Round 1",
                    "start_time":"2026-11-28T08:00:00+00:00","status":"not_started",
                    "sport_event_context":{"stage":{"id":"sr:stage:1"}}}}
            ]},{"x-max-results":"1","x-offset":"0","x-result":"1"})
        if path.endswith("/sport_events/sr:sport_event:99/sport_event_markets.json"):
            return _response({"generated_at":"2026-11-28T10:00:00+00:00","markets":[
                {"id":"sr:market:1","name":"Winner","is_live":False,"books":[
                    {"id":"sr:book:7","name":"Book Seven","removed":False,
                     "outcomes":[{"id":"sr:outcome:1","type":"player_a","odds_decimal":"3.5"}]}
                ]}
            ]})
        return _response({"detail":"unexpected feed"},status=404)

    async def run():
        client=SportradarOddsClient(api_key="test-key",transport=httpx.MockTransport(handler))
        provider=SportradarPrematchProvider(client)
        store=SQLiteMarketStore(tmp_path/"stage-sport.sqlite3")
        orchestrator=IngestionOrchestrator(
            ProviderRegistry([provider]),MarketInventory(),store=store,max_retries=0
        )
        try:
            report=await orchestrator.scan("sportradar-prematch","2026-11-28",package="prematch")
            return report,store
        finally:
            await provider.close()

    report,store=asyncio.run(run())
    assert report.complete
    assert report.stages_discovered==1
    assert report.competitions_discovered==0
    assert report.events_discovered==1 and report.events_scanned==1
    assert report.markets_received==1 and report.selections_received==1
    stages=store.discovery_inventory(provider="sportradar-prematch",stage="stages")
    assert stages[0]["source_id"]=="sr:stage:1"
    snapshots=store.snapshots_for_event("sportradar-prematch","sr:sport_event:99")
    assert len(snapshots)==1
    assert snapshots[0]["markets"][0]["source_book_name"]=="Book Seven"

