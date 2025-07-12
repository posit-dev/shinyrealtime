from pathlib import Path

import folium
import ipyleaflet
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotnine as p9
import seaborn as sns
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, req, ui
from shinywidgets import output_widget, render_widget

from realtime import realtime_server, realtime_ui

load_dotenv()

prompt = (Path(__file__).parent / "prompt.md").read_text()

samples = []

for ds in sns.get_dataset_names():
    df = sns.load_dataset(ds)
    if isinstance(df, pd.DataFrame):
        globals()[ds] = df
        samples.append(f"## {ds}\n\n{df.head().to_csv(index=False)}")

# prompt += "\n\n# Available Datasets\n\n" + "\n\n".join(samples)

data = (
    np.random.normal(size=(100, 3)) * np.array([[1, 1, 1]]) + np.array([[48, 5, 1]])
).tolist()


app_ui = ui.page_fillable(
    realtime_ui("realtime1"),
    output_widget("map", height="500px"),
    ui.output_code("code_text", placeholder=True).add_style(
        "height: 200px; overflow-y: auto;"
    ),
    fillable=True,
)


def server(input: Inputs, output: Outputs, session: Session):
    last_code = reactive.value()

    async def run_python_ipyleaflet_code(code: str):
        """Run Python code that generates a map."""

        last_code.set(code)

    send, send_text = realtime_server(
        "realtime1",
        voice="fable",
        instructions=prompt,
        tools=[run_python_ipyleaflet_code],
        speed=1.1,
    )

    @render_widget
    def map():
        req(last_code())
        return execute_and_return_last(last_code())

    # @reactive.effect
    # async def synchronize_map_view():
    #     if map.widget is not None:
    #         center = map.widget.center
    #         zoom = map.widget.zoom
    #         await send_text(
    #             f"The user has moved the map to center {center} with zoom level {zoom}. Whenever you create a new map, use this center and zoom level."
    #         )

    @render.code
    def code_text():
        req(last_code())
        return last_code()

# Create a namespace for execution
namespace = {}


def execute_and_return_last(code_string):
    """
    Execute multi-line Python code and return the value of the last line.

    Args:
        code_string (str): Multi-line Python code as a string

    Returns:
        The value of the last expression in the code
    """
    # Split the code into lines and remove empty lines
    lines = [line for line in code_string.strip().split("\n") if line.strip()]

    if not lines:
        return None

    # Separate the last line from the rest
    setup_code = "\n".join(lines[:-1])
    last_line = lines[-1].strip()

    # Execute the setup code (all lines except the last)
    if setup_code:
        exec(setup_code, globals(), namespace)

    # Evaluate the last line and return its value
    try:
        # Try to evaluate as an expression first
        result = eval(last_line, globals(), namespace)
        return result
    except SyntaxError:
        # If it's not an expression, execute it and return None
        exec(last_line, globals(), namespace)
        return None

app = App(app_ui, server, debug=False)
