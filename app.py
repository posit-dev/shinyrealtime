import ast
from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import plotnine as p9
import seaborn as sns
import shinychat
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, module, reactive, render, req, ui

from realtime import realtime_server, realtime_ui

load_dotenv()

pricing_gpt4_realtime = {
    "input_text": 4 / 1e6,
    "input_audio": 32 / 1e6,
    "input_image": 5 / 1e6,
    "input_text_cached": 0.4 / 1e6,
    "input_audio_cached": 0.4 / 1e6,
    "input_image_cached": 0.5 / 1e6,
    "output_text": 16 / 1e6,
    "output_audio": 64 / 1e6,
}

pricing_gpt_4o_mini = {
    "input_text": 0.6 / 1e6,
    "input_audio": 10 / 1e6,
    "input_text_cached": 0.3 / 1e6,
    "input_audio_cached": 0.3 / 1e6,
    "output_text": 2.4 / 1e6,
    "output_audio": 20 / 1e6,
}

prompt = (Path(__file__).parent / "prompt.md").read_text()

samples = []

for ds in sns.get_dataset_names():
    df = sns.load_dataset(ds)
    if isinstance(df, pd.DataFrame):
        globals()[ds] = df
        samples.append(f"## {ds}\n\n{df.head(3).to_csv(index=False)}")

prompt += "\n\n# Availble Datasets\n\n" + "\n\n".join(samples)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.help_text(ui.output_text("session_cost", inline=True)),
        shinychat.output_markdown_stream("response_text"),
        title="Transcript",
    ),
    ui.card(
        ui.card_header("Plot"),
        ui.card_body(ui.output_plot("plot", fill=True), padding=0),
        height="66%",
        full_screen=True,
    ),
    ui.card(
        ui.card_header("Code"),
        ui.card_body(ui.output_code("code_text", placeholder=False)),
        height="34%",
        full_screen=True,
    ),
    realtime_ui(
        "realtime1",
        style="z-index: 100000; margin-left: auto; margin-right: auto;",
        right=None,
    ),
    title="VoicePlot",
    fillable=True,
    padding="0",
)


def server(input: Inputs, output: Outputs, session: Session):
    last_code = reactive.value()

    # Setup cost tracking
    running_cost = reactive.value(0)

    async def run_python_plot_code(code: str):
        """Run Python code that generates a plot."""
        last_code.set(code)

    response_text = shinychat.MarkdownStream("response_text")

    realtime_controls = realtime_server(
        "realtime1",
        voice="cedar",
        instructions=prompt,
        tools=[run_python_plot_code],
        speed=1.1,
    )

    greeting = "Welcome to Shiny Realtime!\n\nYou're currently muted; click the mic button to unmute, click-and-hold the mic for push-to-talk, or hold the spacebar key for push-to-talk."

    @reactive.effect
    async def _stream_greeting():
        "Stream a greeting message on startup"

        await response_text.stream([greeting])

    # == Handle realtime events ================================================

    @realtime_controls.on("conversation.item.created")
    async def _show_coding_progress(event: dict[str, Any]):
        "Add notifications when function calls start"

        if event["item"]["type"] == "function_call":
            ui.notification_show(
                "Generating code, please wait...",
                id=event["item"]["id"],
                close_button=False,
            )

    @realtime_controls.on("response.output_item.done")
    async def _hide_coding_progress(event: dict[str, Any]):
        "Remove notifications when function calls complete"

        if event["item"]["type"] == "function_call":
            ui.notification_remove(id=event["item"]["id"])

    @realtime_controls.on("response.done")
    async def _track_session_cost(event):
        "Track session cost"

        usage = event.get("response", {}).get("usage", {})
        if not usage:
            return

        input_token_details = usage.get("input_token_details", {})
        output_token_details = usage.get("output_token_details", {})
        cached_tokens_details = input_token_details.get("cached_tokens_details", {})

        current_response = {
            "input_text": input_token_details.get("text_tokens", 0),
            "input_audio": input_token_details.get("audio_tokens", 0),
            "input_image": input_token_details.get("image_tokens", 0),
            "input_text_cached": cached_tokens_details.get("text_tokens", 0),
            "input_audio_cached": cached_tokens_details.get("audio_tokens", 0),
            "input_image_cached": cached_tokens_details.get("image_tokens", 0),
            "output_text": output_token_details.get("text_tokens", 0),
            "output_audio": output_token_details.get("audio_tokens", 0),
        }

        # Calculate cost
        cost = 0
        for k, v in current_response.items():
            if k in pricing_gpt4_realtime:
                cost += v * pricing_gpt4_realtime[k]

        with reactive.isolate():
            running_cost.set(running_cost() + cost)

    @realtime_controls.on("conversation.item.created")
    async def _clear_transcript(event: Dict[str, Any]):
        "Clear the transcript when a new conversation starts"

        print("GOT HERE 1")
        if event["item"]["type"] == "message":
            await response_text.stream([""], clear=True)

    @realtime_controls.on("response.audio_transcript.delta")
    async def _stream_text_to_transcript(event: Dict[str, Any]):
        "Stream text deltas to the transcript"

        print("GOT HERE 2")
        print(event["delta"])
        await response_text.stream([event["delta"]], clear=False)

    # == Outputs ===============================================================

    @render.plot
    def plot():
        req(last_code())
        return exec_with_return(last_code(), globals(), locals())

    @render.code
    def code_text():
        req(last_code())
        return last_code()

    @render.text
    def session_cost():
        return f"Session cost: ${running_cost():.4f}"


def exec_with_return(code: str, globals: dict, locals: dict) -> Any | None:
    a = ast.parse(code)
    last_expression = None
    if a.body:
        if isinstance(a_last := a.body[-1], ast.Expr):
            last_expression = ast.unparse(a.body.pop())
        elif isinstance(a_last, ast.Assign):
            last_expression = ast.unparse(a_last.targets[0])
        elif isinstance(a_last, (ast.AnnAssign, ast.AugAssign)):
            last_expression = ast.unparse(a_last.target)
    exec(ast.unparse(a), globals, locals)
    if last_expression:
        return eval(last_expression, globals, locals)


app = App(app_ui, server, debug=False)
