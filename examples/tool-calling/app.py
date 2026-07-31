# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "python-dotenv",
#     "shiny",
#     "shinyrealtime @ file://${PROJECT_ROOT}/../..",
# ]
# ///

# Minimal runnable example exercising tool calls end-to-end against
# gpt-realtime-2. Two tools cover the paths that changed in PR #8:
#
#   get_weather(city) -> dict. Verifies structured tool output is JSON-
#     serialized so the model sees named fields, not just values.
#   list_stores(city) -> list[dict]. Same, for the tabular case.
#
# Either tool raises for city = "error" so the error branch is exercised;
# the model should relay the actual message rather than a fixed sentinel.

import random

from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, ui
from shinyrealtime import realtime_server, realtime_ui

load_dotenv()

INSTRUCTIONS = (
    "You are a concise weather assistant. When the user asks about weather, "
    "call get_weather(city). When they ask about stores in a city, call "
    "list_stores(city). Always call the tool rather than making up data. "
    "If a tool errors, tell the user exactly what the error said."
)


def get_weather(city: str) -> dict:
    """Get the current weather for a city. Returns a structured record."""
    if city.lower() == "error":
        raise RuntimeError("Weather service is temporarily unavailable for this city.")
    return {
        "city": city,
        "temp_f": random.randint(40, 85),
        "condition": random.choice(["sunny", "cloudy", "rainy", "windy"]),
        "humidity_pct": random.randint(20, 90),
    }


def list_stores(city: str) -> list[dict]:
    """List retail stores in a city. Returns a table of stores."""
    if city.lower() == "error":
        raise RuntimeError("Store directory lookup failed.")
    return [
        {"name": "Downtown", "address": f"100 Main St, {city}", "open_now": True},
        {"name": "Airport", "address": f"500 Airport Rd, {city}", "open_now": True},
        {"name": "Suburb", "address": f"42 Maple Ave, {city}", "open_now": False},
    ]


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h5("Try saying:"),
        ui.tags.ul(
            ui.tags.li('"What\'s the weather in Boston?"'),
            ui.tags.li('"List the stores in Chicago."'),
            ui.tags.li('"Get the weather in error." (triggers error path)'),
        ),
        open="always",
    ),
    realtime_ui("rt"),
    title="shinyrealtime tool-calling example",
)


def server(input: Inputs, output: Outputs, session: Session):
    realtime_server(
        "rt",
        model="gpt-realtime-2",
        instructions=INSTRUCTIONS,
        tools=[get_weather, list_stores],
    )


app = App(app_ui, server)
