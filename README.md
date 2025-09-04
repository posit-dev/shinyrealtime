# shinyrealtime

A package for integrating OpenAI's [Realtime API](https://platform.openai.com/docs/guides/realtime) with [Shiny](https://shiny.posit.co) applications in both R and Python.

The Realtime API allows you to build conversational chatbots that let users talk in a natural way, less like dictating a text message and more like chatting with a human. The chatbot waits for natural pauses in the user's speech before responding, and the user can interrupt the chatbot at any time by starting to speak again.

Other features of the Realtime API:

- Excellent text-to-speech synthesis
- Supports multiple languages
- Natural sounding speech-to-text
- Gracefully handles user interruption
- Function calling/tool calling

**Note that for security reasons, shinyrealtime apps will NOT work when viewed from an IDE like RStudio, Positron, or VS Code (as these IDEs do not allow iframes to access microphones). You must open the app a real web browser.**

## Project Structure

This repository contains both R and Python packages:

- `pkg-r/`: R package
- `pkg-py/`: Python package
- `src/`: TypeScript source code shared between packages

## Installation

### R Package

```r
# Install from GitHub
remotes::install_github("jcheng5/shinyrealtime/pkg-r")
```

### Python Package

```bash
# Install from GitHub
uv pip install git+https://github.com/jcheng5/shinyrealtime.git
```

## API Key

shinyrealtime requires the `OPENAI_API_KEY` environment variable to be set. You can put it in an `.env` file in your Shiny app directory:

```
OPENAI_API_KEY=<your_api_key>
```

For R, add the following code to your app.R (it has the side-effect of loading the `.env` file):

```r
library(dotenv)
```

For Python, install the `python-dotenv` package and add this near the top of your app.py:

```python
from dotenv import load_dotenv

load_dotenv()
```

## Demo

To run the demo apps (requires a .env file in the root of this repo, as described in the previous section):

```bash
# R demo
make demo-r
```

```bash
# Python demo
make demo-py
```

## Development

To build both packages:

```bash
make build
```

To install both packages:

```bash
make install
```

## License

MIT