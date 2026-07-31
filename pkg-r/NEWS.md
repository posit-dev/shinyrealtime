# shinyrealtime (development version)

## New features

* `realtime_server()` now passes the configured `model` from the server to the JS client, so newer models such as `gpt-realtime-2` can be used instead of the previously hardcoded `gpt-realtime`.
* Tool-call handler now emits `function_call_output` followed by `response.create` after each tool executes, matching the `gpt-realtime-2` requirement (without this the model treats the call as still in-flight and never continues its turn). `send_function_call_output()` bundles both events so tool-call sites don't have to.
* Tool outputs that are lists or data frames are now JSON-serialized via `jsonlite::toJSON(auto_unbox = TRUE)` before being sent to the model. Previously `as.character()` deparsed them, losing list names and emitting literal R source for data frames.

## Bug fixes

* Tool-call error branch now forwards the actual `conditionMessage(e)` to the model instead of a fixed `"ERROR_HANDLED"` sentinel, so the model can tell the user what went wrong.
* Fixed `send()` producing nested JSON arrays (`[[{e1},{e2}]]`) because all callers wrapped events in `list(...)` while the function signature already collected `...`. The Realtime API silently dropped these malformed events. `send()` now unwraps a single unnamed-list argument for backward compatibility.
* `response.create` payloads now serialize as `{}` instead of `[]`; the Realtime API rejected the array form and silently closed the data channel.
* `send_text()` now emits the correct event type `conversation.item.create` (was previously `conversation_item.create`, which the API ignored).
* Replaced a crash-prone `shiny::printStackTrace` call with `message()`.
