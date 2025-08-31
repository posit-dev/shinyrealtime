import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Tuple, Union

import aiohttp
import chatlas
import openai.types.beta.realtime as oair
from faicons import icon_svg
from htmltools import HTMLDependency
from pydantic import TypeAdapter
from shiny import Inputs, Outputs, Session, module, reactive, render, ui

from events import EventEmitter


def dep() -> HTMLDependency:
    return HTMLDependency(
        name="shinyrealtime",
        version="0.1.0",
        source={"subdir": "www"},
        script=[{"src": "app.js"}],
        stylesheet=[{"href": "app.css"}],
    )


@module.ui
def realtime_ui(*, top=None, right="16px", bottom="16px", left=None, **kwargs):
    return ui.TagList(
        ui.div(
            dep(),
            ui.panel_fixed(
                ui.tags.button(
                    ui.tags.span(icon_svg("microphone"), class_="mic-on"),
                    ui.tags.span(icon_svg("microphone-slash"), class_="mic-off"),
                    id=module.resolve_id("mic_button"),
                    class_="btn btn-secondary mic-toggle-btn",
                    title="Click to toggle mic, hold for push-to-talk, or use spacebar",
                ),
                top=top,
                right=right,
                bottom=bottom,
                left=left,
                width="auto",
                class_="text-center",
            ),
            class_="shinyrealtime",
            id=module.resolve_id("key"),
            **kwargs,
        ),
        # ui.input_text("msg", "Message"),
        # ui.input_action_button("send", "Send"),
    )


@module.server
def realtime_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    *,
    model: str = "gpt-realtime",
    voice: Literal[
        "alloy",
        "ash",
        "ballad",
        "cedar",
        "coral",
        "echo",
        "fable",
        "marin",
        "nova",
        "onyx",
        "sage",
        "shimmer",
    ] = "marin",
    speed: float = 1.0,
    instructions: str = "",
    tools: list[Callable[..., Any]] = [],
    api_key: str | None = None,
    **kwargs: Any,
):
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    tools_by_name = {tool.__name__: tool for tool in tools}
    current_event = reactive.value()

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
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "session": {
                        "type": "realtime",
                        "model": model,
                        "instructions": instructions,
                        "audio": {
                            "input": {
                                # TODO: Consider turning off detection when push-to-talk is used
                                "turn_detection": {"type": "semantic_vad"}
                            },
                            "output": {
                                "voice": voice,
                                "speed": speed
                            }
                        },
                        "tools": [
                            chatlas._tools.func_to_schema(tool)["function"]
                            | {"type": "function"}
                            for tool in tools
                        ]
                    }
                }
                | kwargs,
            ) as response:
                data = await response.json()
                # print(data)
                return data["value"]

    @reactive.Effect
    @reactive.event(input.key_event)
    async def handle_event():
        try:
            from openai._models import construct_type_unchecked

            # This is a oair.RealtimeServerEvent but actually using it caused
            # validation errors all the time
            event = json.loads(input.key_event())
            current_event.set(event)
        except Exception as e:
            print(f"Event: {input.key_event()}")
            print(f"Error processing event: {e}")
            await send_text("The function call you sent was malformed, try again?")

        print("-------------")
        print(event["type"])
        print(input.key_event())

        try:
            if event["type"] == "response.function_call_arguments.done":
                fname = event["name"]
                if fname not in tools_by_name:
                    raise ValueError(f"Unknown function: {fname}")
                tool = tools_by_name[fname]
                args = json.loads(event["arguments"])
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

    # Create event emitter
    emitter = EventEmitter()

    # Add on() method to realtime_controls
    def on(
        event_type: str,
    ) -> Callable[[Callable[[dict[str, Any]], None]], Callable[[], None]]:
        def wrapper(callback: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
            return emitter.on(event_type, callback)

        return wrapper

    # Handle events from the reactive value
    @reactive.effect
    async def _handle_event():
        event = current_event()
        if event:
            await emitter.emit(event["type"], event)

    # Create the return object and attach event emitter functionality
    realtime_controls = RealtimeControls(
        send=send,
        send_text=send_text,
        current_event=current_event,
        on=on,
    )

    return realtime_controls

@dataclass
class RealtimeControls:
    send: Callable[
        [Union[oair.ConversationItemCreateEvent, oair.ResponseCreateEvent]], Any
    ]
    send_text: Callable[[str], Any]
    current_event: reactive.Value
    on: Callable[
        [str], Callable[[Callable[[dict[str, Any]], None]], Callable[[], None]]
    ]