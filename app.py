import ast
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import plotnine as p9
import seaborn as sns
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui

from realtime import realtime_server, realtime_ui

load_dotenv()

prompt = (Path(__file__).parent / "prompt.md").read_text()

samples = []

for ds in sns.get_dataset_names():
    df = sns.load_dataset(ds)
    if isinstance(df, pd.DataFrame):
        globals()[ds] = df
        samples.append(f"## {ds}\n\n{df.head().to_csv(index=False)}")

prompt += "\n\n# Availble Datasets\n\n" + "\n\n".join(samples)

app_ui = ui.page_fillable(
    ui.card(
        ui.card_header("Plot"),
        ui.card_body(ui.output_plot("plot", fill=True), padding=0),
        full_screen=True,
    ),
    ui.card(
        ui.card_header("Code"),
        ui.card_body(ui.output_code("code_text", placeholder=True)),
        full_screen=True,
    ),
    realtime_ui(
        "realtime1",
        style="z-index: 100000; margin-left: auto; margin-right: auto;",
        right=None,
    ),
    style="--spacing: 1rem; padding-bottom: 0;",
)


def server(input: Inputs, output: Outputs, session: Session):
    last_code = reactive.value()

    async def run_python_plot_code(code: str):
        """Run Python code that generates a plot."""

        last_code.set(code)

    send, send_text, event = realtime_server(
        "realtime1",
        voice="cedar",
        instructions=prompt,
        tools=[run_python_plot_code],
        speed=1.1,
    )

    @reactive.effect
    def handle_notifications():
        """Shows notification when the model is generating code."""

        evt = event()
        if evt is None:
            return

        if (
            evt["type"] == "conversation.item.created"
            and evt["item"]["type"] == "function_call"
        ):
            ui.notification_show(
                "Generating code, please wait...",
                id=evt["item"]["id"],
                close_button=False,
            )
        elif (
            evt["type"] == "response.output_item.done"
            and evt["item"]["type"] == "function_call"
        ):
            ui.notification_remove(id=evt["item"]["id"])

    @render.plot
    def plot():
        req(last_code())
        print("Plotting:")
        print(last_code())
        return exec_with_return(last_code(), globals(), locals())

    @render.code
    def code_text():
        req(last_code())
        return last_code()

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
