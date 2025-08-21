import asyncio
import numpy as np
import websockets
from .base_sink import BaseAudioSink

class WebSocketAudioSink(BaseAudioSink):
    """
    An audio sink that sends raw audio chunks as binary messages over a
    pre-existing WebSocket connection using a pure asyncio approach.

    This component is a generic "sender" and does not manage the WebSocket
    connection lifecycle. It runs its sending logic in a concurrent asyncio.Task.
    """

    def __init__(self, websocket, sample_rate=16000, channels=1, dtype='int16', blocksize=None):
        """
        Initializes the WebSocketAudioSink.

        Args:
            websocket: An active `websockets` connection object.
            sample_rate, channels, dtype, blocksize: Passed to BaseAudioSink.
        """
        super().__init__(sample_rate, channels, dtype, blocksize)
        if not websocket:
            raise ValueError("A valid websocket connection object is required.")
        self._websocket = websocket
        self._send_task = None

    async def start(self):
        """
        Starts the background task that sends audio from the buffer.
        Note: This does not establish a connection, which must be done beforehand.
        """
        if self._send_task is not None:
            print("WebSocketAudioSink: Sender is already running.")
            return

        print("WebSocketAudioSink: Starting send task.")
        self._send_task = asyncio.create_task(self._send_loop_async())

    async def _send_loop_async(self):
        """The sending logic that runs as a concurrent asyncio task."""
        try:
            while not self._is_closed.is_set():
                try:
                    # Get a chunk from the buffer
                    chunk = self._buffer.popleft()
                    # Directly await the send operation
                    await self._websocket.send(chunk.tobytes())
                except IndexError:
                    # Buffer is empty, wait a moment for more data without blocking
                    await asyncio.sleep(0.005)
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocketAudioSink: Connection closed during send. Stopping task.")
                    break
        except asyncio.CancelledError:
            print("WebSocketAudioSink: Send task was cancelled.")
        except Exception as e:
            # Catch any other exception, log it, and stop the task
            print(f"WebSocketAudioSink: Error in send loop: {e}. Stopping task.")
        finally:
            self._is_closed.set()
            print("WebSocketAudioSink: Send loop finished.")


    def close(self):
        """
        Stops the sink's internal operations by cancelling the send task.
        Note: This does NOT close the WebSocket connection itself. The creator
        of the connection is responsible for closing it.
        """
        if not self._is_closed.is_set():
            super().close()
            print("WebSocketAudioSink: Stopping...")
            if self._send_task and not self._send_task.done():
                self._send_task.cancel()
            print("WebSocketAudioSink: Stopped.")

    async def wait_until_stopped(self):
        """A utility to wait for the send task to finish after being cancelled."""
        if self._send_task:
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass # This is expected
