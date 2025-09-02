# shinyrealtime

A Python package for integrating OpenAI's Real-Time API with Shiny applications.

## Installation

You can install the development version of shinyrealtime from GitHub:

```bash
pip install git+https://github.com/jcheng5/shinyrealtime.git#subdirectory=pkg-py
```

## Usage

```python
from shiny import App, ui
from shinyrealtime import realtime_ui, realtime_server

app_ui = ui.page_fluid(
    ui.panel_title("Realtime API Demo"),
    realtime_ui(top=None, right="16px", bottom="16px", left=None),
    ui.output_text("output"),
)

def server(input, output, session):
    rt = realtime_server(
        model="gpt-realtime",
        instructions="You are a helpful assistant."
    )
    
    @rt.on("response.text.content")
    async def on_text(event):
        output.output.set(event["text"])

app = App(app_ui, server)
```

## License

MIT