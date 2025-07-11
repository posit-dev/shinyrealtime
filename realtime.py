import asyncio
import json
import os
from typing import Any, Callable, Literal

import aiohttp
import chatlas
import openai.types.beta.realtime as oair
from htmltools import HTMLDependency
from pydantic import TypeAdapter
from shiny import Inputs, Outputs, Session, module, reactive, render, ui


def dep() -> HTMLDependency:
    return HTMLDependency(
        name="shinyrealtime",
        version="0.1.0",
        source={"subdir": "www"},
        script=[{"src": "app.js"}],
        stylesheet=[{"href": "app.css"}],
    )


@module.ui
def realtime_ui():
    return ui.TagList(
        ui.div(dep(), class_="shinyrealtime", id=module.resolve_id("key")),
        # ui.input_text("msg", "Message"),
        # ui.input_action_button("send", "Send"),
    )


@module.server
def realtime_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    model: str = "gpt-4o-realtime-preview-2025-06-03",
    voice: Literal[
        "alloy",
        "ash",
        "ballad",
        "coral",
        "echo",
        "fable",
        "nova",
        "onyx",
        "sage",
        "shimmer",
    ] = "alloy",
    instructions: str | None = None,
    tools: list[Callable[..., Any]] = [],
    api_key: str | None = None,
    **kwargs: Any,
):
    tools_by_name = {tool.__name__: tool for tool in tools}

    @reactive.effect
    @reactive.event(input.send)
    async def send_message():
        send_text(input.msg())

    async def send_text(text: str):
        await send(
            oair.ConversationItemCreateEvent(
                item=oair.ConversationItem(
                    role="user",
                    content=[
                        oair.ConversationItemContent(
                            type="input_text",
                            text=text,
                        )
                    ],
                ),
            ),
            oair.ResponseCreateEvent(response={}),
        )

    @output(suspend_when_hidden=False)
    @render.text
    async def key():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {api_key or os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "instructions": instructions,
                    "model": model,
                    "turn_detection": {"type": "semantic_vad"},
                    "tools": [
                        chatlas._tools.func_to_schema(tool)["function"]
                        | {"type": "function"}
                        for tool in tools
                    ],
                }
                | kwargs,
            ) as response:
                data = await response.json()
                if "client_secret" not in data:
                    print(data)
                return data["client_secret"]["value"]

    @reactive.effect
    @reactive.event(input.key_event)
    async def _():
        try:
            from openai._models import construct_type_unchecked

            event = construct_type_unchecked(
                value=json.loads(input.key_event()), type_=oair.RealtimeServerEvent
            )
        except Exception as e:
            print(f"Event: {input.key_event()}")
            print(f"Error processing event: {e}")
            await send_text("The function call you sent was malformed, try again?")

        print("-------------")
        print(event.type)
        print(input.key_event())

        try:
            if event.type == "response.function_call_arguments.done":
                fname = event.name
                if fname not in tools_by_name:
                    raise ValueError(f"Unknown function: {fname}")
                tool = tools_by_name[fname]
                args = json.loads(event.arguments)
                # If the tool is async, we need to await it
                if asyncio.iscoroutinefunction(tool):
                    _result = await tool(**args)
                else:
                    _result = tool(**args)
                # TODO: Return the result to the model?
        except Exception as e:
            await send_text(f"Error processing function call: {e}")

    async def send(*events: dict[str, Any]):
        await session.send_custom_message("realtime_send", events)

    return send, send_text
