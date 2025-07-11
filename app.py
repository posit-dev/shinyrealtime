from pathlib import Path

import matplotlib as mpl
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
    realtime_ui("realtime1"),
    ui.output_plot("plot", fill = True),
    ui.div(
        ui.output_code("code_text", placeholder=False),
        style="height: 300px; max-height: 300px; overflow-y: auto; margin-bottom: 20px;",
    ),
    fillable = True,
)


def server(input: Inputs, output: Outputs, session: Session):
    last_code = reactive.value()

    async def run_python_plot_code(code: str):
        """Run Python code that generates a plot."""

        last_code.set(code)

    send, send_text = realtime_server(
        "realtime1",
        voice="fable",
        instructions=prompt,
        tools=[run_python_plot_code],
        speed=1.1,
    )

    @render.plot
    def plot():
        req(last_code())
        print("Plotting:")
        print(last_code())
        return exec(last_code(), globals())

    @render.code
    def code_text():
        req(last_code())
        return last_code()


app = App(app_ui, server, debug=False)
