# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "matplotlib",
#     "pandas",
#     "plotnine",
#     "seaborn",
#     "shinychat",
#     "python-dotenv",
#     "shiny",
#     "shinyrealtime @ file://${PROJECT_ROOT}",
# ]
# ///

import ast
import base64
from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import plotnine as p9
import seaborn as sns
import shinychat
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shinyrealtime import realtime_server, realtime_ui

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


def hidden_audio_el(id: str, file_path: str, media_type: str = "audio/mp3"):
    """Create a hidden HTML audio element with embedded audio data."""
    file_path = Path(file_path)
    if not file_path.exists():
        return ui.HTML("")

    # Read binary data from file
    raw_data = file_path.read_bytes()

    # Encode to base64
    base64_data = base64.b64encode(raw_data).decode("utf-8")

    # Create data URI
    data_uri = f"data:{media_type};base64,{base64_data}"

    # Return HTML audio element
    return ui.HTML(
        f'<audio id="{id}" src="{data_uri}" style="display:none;" preload="auto"></audio>'
    )


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
        ui.card_body(ui.output_ui("plot_container", fill=True), padding=0),
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
    hidden_audio_el("shutter", "shutter.mp3"),
    title="VoicePlot",
    fillable=True,
    padding="0",
)


def server(input: Inputs, output: Outputs, session: Session):
    last_code = reactive.value()
    interaction_mode = reactive.value("none")

    # Setup cost tracking
    running_cost = reactive.value(0)

    async def run_python_plot_code(code: str):
        """Run Python code that generates a plot."""

        last_code.set(code)

    def set_plot_interaction_mode(mode: str):
        """Set the plot interaction mode.

        When an interaction mode is set, user interactions with the plot
        will be sent back to the assistant as text messages.

        Args:
            mode: The interaction mode to set. One of 'none', 'click', or 'brush'.
        """
        interaction_mode.set(mode)

        if mode == "click":
            ui.notification_show(
                "Plot interaction mode set to 'click'. Click on the plot to send click coordinates to the assistant.",
                duration=5,
            )
        elif mode == "brush":
            ui.notification_show(
                "Plot interaction mode set to 'brush'. Brush a region on the plot to send brush coordinates to the assistant.",
                duration=5,
            )

    response_text = shinychat.MarkdownStream("response_text")

    realtime_controls = realtime_server(
        "realtime1",
        voice="cedar",
        instructions=prompt,
        tools=[run_python_plot_code, set_plot_interaction_mode],
        speed=1.1,
    )

    greeting = "Welcome to Shiny Realtime!\n\nYou're currently muted; click the mic button to unmute, click-and-hold the mic for push-to-talk, or hold the spacebar key for push-to-talk."

    # Track progress indicator
    progress = None

    @reactive.effect
    async def _stream_greeting():
        "Stream a greeting message on startup"

        await response_text.stream([greeting])

    # == Handle realtime events ================================================

    @realtime_controls.on("response.created")
    async def _show_progress(event: dict[str, Any]):
        "Show progress indicator when response starts"
        nonlocal progress

        progress = ui.Progress()
        progress.set(value=None, message="Thinking...")

    @realtime_controls.on("response.done")
    async def _hide_progress(event: dict[str, Any]):
        "Hide progress indicator when response completes"
        nonlocal progress

        if progress is not None:
            progress.close()
            progress = None

    @realtime_controls.on("conversation.item.added")
    async def _show_coding_progress(event: dict[str, Any]):
        "Add notifications when function calls start"

        if event["item"]["type"] == "function_call":
            nonlocal progress
            if progress is not None:
                progress.set(message="Generating code, please wait...")

    @realtime_controls.on("conversation.item.done")
    async def _hide_coding_progress(event: dict[str, Any]):
        "Remove notifications when function calls complete"

        # No need to explicitly remove notifications with the progress indicator approach

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

    @realtime_controls.on("response.created")
    async def _clear_transcript(event: Dict[str, Any]):
        "Clear the transcript when a new response starts"

        await response_text.stream([""], clear=True)

    @realtime_controls.on("response.output_audio_transcript.delta")
    async def _stream_text_to_transcript(event: Dict[str, Any]):
        "Stream text deltas to the transcript"

        await response_text.stream([event["delta"]], clear=False)

    @reactive.effect
    @reactive.event(input.plot_click)
    async def _handle_plot_click():
        "Handle plot clicks and send them to the assistant"

        await realtime_controls.send_text(
            f"(The user clicked on the plot at data coordinates ({input.plot_click()['x']}, {input.plot_click()['y']}).)\n",
            force_response=True,
        )

    @reactive.effect
    @reactive.event(input.plot_brush)
    async def _handle_plot_brush():
        "Handle plot brushing and send the brush coordinates to the assistant"

        brush = input.plot_brush()
        await realtime_controls.send_text(
            f"(The user brushed a region on the plot from data coordinates ({brush['xmin']}, {brush['ymin']}) to ({brush['xmax']}, {brush['ymax']}).)\n",
            force_response=True,
        )

    # == Outputs ===============================================================
    @render.ui
    def plot_container():
        click_opts = False
        brush_opts = False
        if interaction_mode() == "click":
            click_opts = ui.click_opts(clip=False)
        elif interaction_mode() == "brush":
            brush_opts = ui.brush_opts(reset_on_new=True)

        return ui.output_plot("plot", click=click_opts, brush=brush_opts, fill=True)

    @render.plot
    def plot():
        req(last_code())
        result = exec_with_return(last_code(), globals(), locals())

        return result

    @reactive.effect(priority=-10)
    async def play_shutter():
        req(last_code())
        await session.send_custom_message("play_audio", {"selector": "#shutter"})

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

if __name__ == "__main__":
    app.run(launch_browser=True, port=0)
