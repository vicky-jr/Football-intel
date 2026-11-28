import asyncio
import httpx

from app.providers.sportradar import SportradarOddsClient, SportradarPrematchProvider
from scripts.check_sportradar_access import inspect_access


def test_access_check_reports_only_tier_and_catalogue_counts():
    def handler(request):
        if request.url.path.endswith("/books.json"):
            return httpx.Response(200, json={"books":[
                {"id":"secret-book-1","name":"Book One"},
                {"id":"secret-book-2","name":"Book Two"}
            ]}, headers={"x-origin-id":"MARKET_ORIGIN_CORE_CRAWLERS"})
        if request.url.path.endswith("/sports.json"):
            return httpx.Response(200, json={"sports":[
                {"id":"sport-1","name":"Football","type":"competition"},
                {"id":"sport-2","name":"Golf","type":"stage"},
                {"id":"sport-3","name":"Basketball","type":"competition"},
            ]})
        return httpx.Response(404, json={"error":"unexpected"})
    async def run():
        client=SportradarOddsClient(api_key="test-api-key",transport=httpx.MockTransport(handler))
        provider=SportradarPrematchProvider(client)
        return await inspect_access(provider)
    result=asyncio.run(run())
    assert result["authenticated"] is True
    assert result["access_tier"]=="oc_core"
    assert result["books_discovered"]==2
    assert result["sports_discovered"]==3
    assert result["competition_based_sports"]==2
    assert result["stage_based_sports"]==1
    assert "books" not in result
    assert result["api_key_logged"] is False
