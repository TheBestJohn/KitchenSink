
import asyncio
import numpy as np
import websockets
import json
import base64
import threading
import time
from .base_sink import BaseAudioSink

class TypedWebSocketClientAudioSink(BaseAudioSink):
    """
    An audio sink that connects to a typed WebSocket server and sends
    both audio (as Base64 JSON) and other message types.
    """

    def __init__(self, uri, sample_rate=16000, channels=1, dtype='int16', blocksize=None):
        """
        Initializes the TypedWebSocketClientAudioSink.

        Args:
            uri (str): The WebSocket URI to connect to (e.g., "ws://localhost:8765").
            sample_rate, channels, dtype, blocksize: Passed to BaseAudioSink.
        """
        super().__init__(sample_rate, channels, dtype, blocksize)
        self.uri = uri
        self._websocket = None
        self._loop = None
        # We no longer need a dedicated send thread for audio, 
        # as push_chunk will now use the general-purpose send_message.
        # However, we keep a lock to ensure thread-safety for sending messages.
        self._send_lock = asyncio.Lock()

    async def start(self):
        """Establishes the connection to the WebSocket server."""
        print(f"TypedWebSocketClient: Attempting to connect to {self.uri}...")
        try:
            self._websocket = await websockets.connect(self.uri)
            self._loop = asyncio.get_running_loop()
            print("TypedWebSocketClient: Connection successful.")
        except ConnectionRefusedError:
            print(f"TypedWebSocketClient: Connection refused by {self.uri}.")
            self.close()
            raise

    def push_chunk(self, chunk: np.ndarray):
        """
        Receives an audio chunk, encodes it, and schedules it to be sent.
        This is designed to be called from a non-async (e.g., audio callback) thread.
        """
        if self._is_closed.is_set() or not self._loop:
            return

        # Encode audio data as a Base64 string
        audio_b64 = base64.b64encode(chunk.tobytes()).decode('utf-8')
        
        # Schedule the send_message coroutine to run on the event loop
        asyncio.run_coroutine_threadsafe(
            self.send_message("audio", audio_b64),
            self._loop
        )

    async def send_message(self, msg_type: str, payload):
        """
        Sends a typed message to the WebSocket server. This method is a coroutine
        and must be awaited.

        Args:
            msg_type (str): The type of the message (e.g., "audio", "text").
            payload: The data to send. Must be JSON-serializable.
        """
        if self._is_closed.is_set() or not self._websocket or not self._websocket.open:
            print("Cannot send message, connection is closed.")
            return

        message = {
            "type": msg_type,
            "payload": payload
        }
        
        async with self._send_lock:
            try:
                await self._websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                print("Failed to send message: Connection is closed.")
                self.close()

    def close(self):
        """Closes the WebSocket connection."""
        if not self._is_closed.is_set():
            super().close()
            print("TypedWebSocketClient: Closing connection...")
            if self._websocket:
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._websocket.close(), self._loop)
            print("TypedWebSocketClient: Connection closed.")
