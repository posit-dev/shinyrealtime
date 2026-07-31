# Tool-calling example (`gpt-realtime-2`)

A minimal end-to-end example exercising tool calls against `gpt-realtime-2`,
in both R and Python. Set up as a runnable check for the changes in PR #8.

## What it covers

Two tools, each with a happy path and an error path:

| Tool | Return type | Verifies |
|---|---|---|
| `get_weather(city)` | named record (dict / R list) | Structured output is JSON-serialized before being handed to the model, so field names survive. |
| `list_stores(city)` | table (list of dicts / R data.frame) | Same, for the tabular case that used to serialize as literal R source. |

Either tool raises when `city == "error"`, so the error branch also gets
exercised — the model should relay the actual exception message rather than
a fixed `"ERROR_HANDLED"` sentinel.

## Running

Set `OPENAI_API_KEY` (or put it in a `.env` file next to the example).

**R:**
```sh
cd examples/tool-calling
R -e 'shiny::runApp("app.R", launch.browser = TRUE)'
```

**Python:**
```sh
cd examples/tool-calling
shiny run --launch-browser app.py
```

## What to say

Click the mic button and try:

- *"What's the weather in Boston?"* — expect the model to speak back the
  city, temperature, condition, and humidity from the returned record.
- *"List the stores in Chicago."* — expect the model to read off store
  names / addresses from the returned table. If the model reads only
  values with no field names, the structured-output fix regressed.
- *"Get the weather in error."* — expect the model to say something like
  *"Weather service is temporarily unavailable for this city."* If it
  instead says something generic like "an error occurred," the
  error-message forwarding fix regressed.
