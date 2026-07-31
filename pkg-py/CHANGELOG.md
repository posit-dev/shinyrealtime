# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added
- `realtime_server()` now passes the configured `model` from the R/Python side through to the JS client, so newer models like `gpt-realtime-2` can be used instead of the previously hardcoded `gpt-realtime`.
- Tool-call handler now emits `function_call_output` followed by `response.create` after each tool executes, matching the `gpt-realtime-2` requirement (without this, the model treats the call as still in-flight and never continues its turn).
- JS `Connection.send()` queues outgoing events while the WebRTC data channel is still connecting and flushes them on `open`, fixing a `RTCDataChannel.readyState is not 'open'` DOMException race that appeared with the new post-tool-execution sends.

### Fixed
- Tool-call error branch now forwards the actual exception message to the model instead of a fixed `"ERROR_HANDLED"` sentinel, so the model can tell the user what went wrong.
- `response.create` payloads now serialize as `{}` instead of `[]`; the Realtime API rejected the array form and silently closed the data channel.
- `send_text` now emits the correct event type `conversation.item.create` (was previously `conversation_item.create`, which the API ignored).
- Replaced a crash-prone `shiny::printStackTrace` call with `message()` (R side).

## 0.1.0 - 2024-08-31

### Added
- Initial release of shinyrealtime package
- Support for real-time audio and text interactions with OpenAI's Real-Time API
- Support for tool calling functionality
- Event system for handling real-time events
- Microphone button with push-to-talk functionality