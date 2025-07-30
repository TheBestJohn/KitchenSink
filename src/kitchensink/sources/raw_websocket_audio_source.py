
import asyncio
import numpy as np
import websockets
from .base_source import BaseAudioSource

class RawWebSocketServerAudioSource(BaseAudioSource):
    """
    An audio source that listens for a single WebSocket client,
    receives raw binary audio messages, and forwards them to a sink.
    This component is optimized for performance and expects only audio data.
    """

    def __init__(self, sink, disconnect_callback=None, host='0.0.0.0', port=8765, blocksize=None):
        """
        Initializes the RawWebSocketServerAudioSource.

        Args:
            sink, disconnect_callback: Passed to BaseAudioSource.
            host (str): The host address to listen on.
            port (int): The port to listen on.
            blocksize (int, optional): The preferred blocksize for audio chunks.
                                       Note: This source processes whatever it receives.
        """
        super().__init__(sink, disconnect_callback, blocksize=blocksize)
        self.host = host
        self.port = port
        self.server_task = None
        self.server = None

    async def _handler(self, websocket):
        """
        Handles the WebSocket connection for a single client.
        """
        print(f"WebSocket client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                # We expect the incoming messages to be binary audio data
                if isinstance(message, bytes):
                    # Convert the bytes to a NumPy array and push to the sink
                    audio_chunk = np.frombuffer(message, dtype=np.int16)
                    self.sink(audio_chunk)
                else:
                    print(f"Warning: Received non-binary message: {message}")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocket client disconnected: {e}")
        except Exception as e:
            print(f"An error occurred in the WebSocket handler: {e}")
        finally:
            if self.disconnect_callback:
                self.disconnect_callback()

    async def start(self):
        """Starts the WebSocket server."""
        if self.server_task is not None:
            print("WebSocket server is already running.")
            return

        try:
            print(f"Starting WebSocket audio source server on {self.host}:{self.port}")
            self.server = await websockets.serve(self._handler, self.host, self.port)
            # Keep a reference to the task to allow stopping it
            self.server_task = asyncio.create_task(self.server.wait_closed())
        except Exception as e:
            print(f"Failed to start WebSocket server: {e}")
            self.server_task = None
            self.server = None


    async def stop(self):
        """Stops the WebSocket server gracefully."""
        if self.server:
            print("Stopping WebSocket server...")
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            self.server_task = None
            print("WebSocket server stopped.")
