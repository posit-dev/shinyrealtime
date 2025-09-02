# shinyrealtime

A package for integrating OpenAI's Real-Time API with Shiny applications in both R and Python.

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
pip install git+https://github.com/jcheng5/shinyrealtime.git
```

## Requirements

This project requires the `OPENAI_API_KEY` environment variable to be set. You can put it in an `.env` file in the root directory:

```
OPENAI_API_KEY=<your_api_key>
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

To run the demo apps:

```bash
# R demo
Rscript app.R

# Python demo
shiny run app.py --launch-browser
```

**Note that for security reasons, these demo apps (and any shinyrealtime apps) will NOT work when the UI is loaded in an IDE like RStudio, Positron, or VS Code (as these IDEs do not allow iframes to access microphones). You must open the app a real web browser.**

## License

MIT