
import asyncio
import numpy as np
import websockets
import threading
import time
from .base_sink import BaseAudioSink

class RawWebSocketClientAudioSink(BaseAudioSink):
    """
    An audio sink that connects to a WebSocket server and sends raw audio chunks
    as binary messages. This component is optimized for performance.
    """

    def __init__(self, uri, sample_rate=16000, channels=1, dtype='int16', blocksize=None):
        """
        Initializes the RawWebSocketClientAudioSink.

        Args:
            uri (str): The WebSocket URI to connect to (e.g., "ws://localhost:8765").
            sample_rate, channels, dtype, blocksize: Passed to BaseAudioSink.
        """
        super().__init__(sample_rate, channels, dtype, blocksize)
        self.uri = uri
        self._websocket = None
        self._loop = None
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)

    async def start(self):
        """Establishes the connection to the WebSocket server."""
        print(f"WebSocketClientAudioSink: Attempting to connect to {self.uri}...")
        try:
            self._websocket = await websockets.connect(self.uri)
            self._loop = asyncio.get_running_loop()
            self._send_thread.start()
            print("WebSocketClientAudioSink: Connection successful.")
        except ConnectionRefusedError:
            print(f"WebSocketClientAudioSink: Connection refused by {self.uri}.")
            self.close()
            raise
        except Exception as e:
            print(f"WebSocketClientAudioSink: An unexpected error occurred: {e}")
            self.close()
            raise

    def _send_loop(self):
        """The sending logic that runs in a separate thread."""
        while not self._is_closed.is_set():
            try:
                chunk = self._buffer.popleft()
                if self._websocket and self._websocket.open:
                    future = asyncio.run_coroutine_threadsafe(self._send_chunk(chunk), self._loop)
                    future.result()  # Wait for the send to complete
            except IndexError:
                time.sleep(0.005)
            except Exception as e:
                print(f"WebSocketClientAudioSink: Error in send loop: {e}")
                self.close()

    async def _send_chunk(self, chunk: np.ndarray):
        """Coroutine to send a chunk over the WebSocket."""
        await self._websocket.send(chunk.tobytes())

    def close(self):
        """Closes the WebSocket connection."""
        if not self._is_closed.is_set():
            super().close()
            print("WebSocketClientAudioSink: Closing connection...")
            if self._websocket:
                if self._loop and self._loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self._websocket.close(), self._loop)
                    try:
                        future.result(timeout=2.0)
                    except Exception as e:
                        print(f"WebSocketClientAudioSink: Error during close: {e}")
                else:
                    # Fallback for when the loop isn't running
                    try:
                        # This is not ideal in an async context but is a last resort
                        asyncio.run(self._websocket.close())
                    except:
                        pass
            
            if self._send_thread.is_alive():
                self._send_thread.join(timeout=1)
            print("WebSocketClientAudioSink: Connection closed.")
