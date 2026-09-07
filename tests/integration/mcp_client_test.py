"""Manual smoke test for src/mcp_server/server.py: lists tools over stdio.

Usage:
    .venv/bin/python tests/integration/mcp_client_test.py
"""

from __future__ import annotations

import pytest
from datetime import datetime
from dotenv import dotenv_values

test_source1 = { "name": "city events", "url": "https://city-events.com/" }
test_source2 = { "name": "jazz city", "url": "https://jazzcity.com/" }
real_source = { "name": "jazz alley", "url": "https://www.jazzalley.com/www-home/calendar.jsp"}

location: str = "Seattle, WA"
length: int = 7
test_generate_calendar_request = {
    "location": location,
    "calendar_length_days": length,
    "max_cost": "25.00",
    "event_types": ["music", "theater"],
    "genres": ["jazz"],
}

@pytest.mark.integration
async def test_list_tools(client):
    async with client as connected:
        result = await connected.session().list_tools()
        for tool in result.tools:
            print(f" * {tool.name}: {tool.description}")
    
        assert len(result.tools) == 4


@pytest.mark.integration
async def test_add_source_tool(client):
    async with client as connected:
        current_datetime = datetime.now()
        result = await connected.session().call_tool("add_source", test_source1)
        source = result.structured_content

        source_datetime = datetime.strptime(source["added_at"], "%Y-%m-%d")
        
        assert test_source1["name"] == source["name"]
        assert test_source1["url"] == source["url"]
        assert source_datetime.year == current_datetime.year

@pytest.mark.integration
async def test_list_sources_tool(client):
    async with client as connected:
        await connected.session().call_tool("add_source", test_source2)
        result = await connected.session().call_tool("list_sources", {})
        sources = result.structured_content["result"]

        assert len(sources) == 1
        
@pytest.mark.integration
async def test_remove_source_tool(client):
    async with client as connected:
        await connected.session().call_tool("add_source", test_source2)
        result = await connected.session().call_tool("remove_source", { "url": test_source2["url"] })
        source = result.structured_content

        assert source["url"] == test_source2["url"]


@pytest.mark.integration
async def test_generate_calendar_tool(client, monkeypatch):
    real_env = dotenv_values(".env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", real_env["ANTHROPIC_API_KEY"])
    monkeypatch.setenv("TAVILY_API_KEY", real_env["TAVILY_API_KEY"])
    
    async with client as connected:
        await connected.session().call_tool("add_source", real_source)
        result = await connected.session().call_tool(
            "generate_calendar", test_generate_calendar_request
        )
        output: str = result.content[0].text
        
        assert location in output
        assert str(length) in output


@pytest.mark.integration
async def test_invalid_cost(client):
    error: str = "max_cost must be a decimal number"
        
    invalid_cost_calendar_request = {
        "location": location,
        "calendar_length_days": length,
        "max_cost": "25.xx",
        "event_types": ["music", "theater"],
        "genres": ["jazz"],
    }    
    
    async with client as connected:
        await connected.session().call_tool("add_source", real_source)
        result = await connected.session().call_tool(
            "generate_calendar", invalid_cost_calendar_request
        )
        output: str = result.content[0].text
        
        assert error in output
        
@pytest.mark.integration
async def test_missing_start_before(client):
    error: str = "start_after and start_before must both be set together"
        
    invalid_cost_calendar_request = {
        "location": location,
        "calendar_length_days": length,
        "max_cost": "25.00",
        "event_types": ["music", "theater"],
        "start_after": "17:00",
        "genres": ["jazz"],
    }    
    
    async with client as connected:
        await connected.session().call_tool("add_source", real_source)
        result = await connected.session().call_tool(
            "generate_calendar", invalid_cost_calendar_request
        )
        output: str = result.content[0].text
        
        assert error in output

@pytest.mark.integration
async def test_invalid_model_key(client):
    error: str = "No trusted sources configured and web search is unavailable"   
    
    async with client as connected:
        await connected.session().call_tool("add_source", real_source)
        result = await connected.session().call_tool(
            "generate_calendar", test_generate_calendar_request
        )
        output: str = result.content[0].text
        print(output)

        assert error in output

@pytest.mark.integration
async def test_no_sources(client, monkeypatch):
    error: str = "No trusted sources configured and web search is unavailable"
    real_env = dotenv_values(".env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", real_env["ANTHROPIC_API_KEY"])

    async with client as connected:
        result = await connected.session().call_tool(
            "generate_calendar", test_generate_calendar_request
        )
        output: str = result.content[0].text
        print(output)

        assert error in output
