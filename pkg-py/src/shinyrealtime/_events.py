import uuid
from typing import Any, Callable, Dict, List, Optional


class AsyncCallbacks:
    """A reusable class for managing async callbacks."""

    def __init__(self):
        self._callbacks = {}

    def register(self, callback: Callable) -> Callable:
        """
        Register a callback function.

        Returns a function that can be called to unregister the callback.
        """
        if not callable(callback):
            raise TypeError("callback must be a function")

        # Generate a unique ID for the callback
        callback_id = str(uuid.uuid4())
        self._callbacks[callback_id] = callback

        # Return an unsubscribe function
        def unsubscribe():
            if callback_id in self._callbacks:
                del self._callbacks[callback_id]

        return unsubscribe

    async def invoke(self, *args, **kwargs):
        """Invoke all registered callbacks with the provided arguments."""
        for callback_id, callback in list(self._callbacks.items()):
            if callback_id in self._callbacks:
                await callback(*args, **kwargs)

    def count(self) -> int:
        """Return the number of registered callbacks."""
        return len(self._callbacks)


class EventEmitter:
    """Event emitter for handling realtime events."""

    def __init__(self):
        self.handlers = {}

    def on(self, event_type: str, callback: Callable) -> Callable:
        """
        Register a handler for an event type.

        Parameters:
        - event_type: The type of event to listen for
        - callback: The function to call when the event occurs

        Returns a function that can be called to unregister the handler.
        """
        if not callable(callback):
            raise TypeError("callback must be a function")

        # Create callbacks container for this event type if it doesn't exist
        if event_type not in self.handlers:
            self.handlers[event_type] = AsyncCallbacks()

        # Register the callback and return the unsubscribe function
        return self.handlers[event_type].register(callback)

    async def emit(self, event_type: str, event: Any):
        """
        Emit an event.

        Parameters:
        - event_type: The type of event to emit
        - event: The event data to pass to handlers
        """
        # Exact match handlers
        if event_type in self.handlers:
            await self.handlers[event_type].invoke(event)

        # Check for wildcard handlers (e.g., "conversation.*")
        event_parts = event_type.split(".")

        for i in range(1, len(event_parts) + 1):
            prefix = ".".join(event_parts[:i])
            wildcard = f"{prefix}.*"

            if wildcard in self.handlers:
                await self.handlers[wildcard].invoke(event)

        # Global wildcard handler
        if "*" in self.handlers:
            await self.handlers["*"].invoke(event)