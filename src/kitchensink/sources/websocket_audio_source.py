import asyncio
import numpy as np
import websockets
from .base_source import BaseAudioSource

class WebSocketAudioSource(BaseAudioSource):
    """
    An audio source that listens for messages on a pre-existing WebSocket
    connection, interprets them as audio, and forwards them to a sink.

    This component is a generic "receiver" and does not manage the WebSocket
    connection lifecycle. It is designed to be used by a WebSocket client or
    server connection handler.
    """

    def __init__(self, sink, websocket, sample_rate=16000, channels=1, dtype='int16', disconnect_callback=None, text_callback=None, blocksize=None):
        """
        Initializes the WebSocketAudioSource.

        Args:
            sink: The callable sink for the audio data.
            websocket: An active `websockets` connection object.
            sample_rate (int): The sample rate of the incoming audio.
            channels (int): The number of channels of the incoming audio.
            dtype (str): The data type of the incoming audio.
            disconnect_callback (callable, optional): Called when the connection ends.
            text_callback (callable, optional): Called when a text message is received.
            blocksize (int, optional): The preferred blocksize for audio chunks.
        """
        super().__init__(
            sink,
            sample_rate=sample_rate,
            channels=channels,
            dtype=dtype,
            disconnect_callback=disconnect_callback,
            blocksize=blocksize
        )
        if not websocket:
            raise ValueError("A valid websocket connection object is required.")
        self.text_callback = text_callback
        self._websocket = websocket
        self._receive_task = None

    async def _receive_loop(self):
        """

        Handles receiving messages from the WebSocket connection.
        """
        print(f"WebSocketAudioSource: Starting to listen for messages from {self._websocket.remote_address}")
        try:
            async for message in self._websocket:
                if isinstance(message, bytes):
                    # Convert bytes to NumPy array before passing to the sink
                    # Note: We must know the dtype from the sender.
                    # We assume it matches this source's dtype setting.
                    chunk = np.frombuffer(message, dtype=self.dtype)
                    await self.sink(chunk)
                elif isinstance(message, str):
                    if self.text_callback:
                        self.text_callback(message)
                    else:
                        print(f"WebSocketAudioSource: Warning: Received unhandled text message.")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocketAudioSource: Client disconnected: {e}")
        except Exception as e:
            print(f"WebSocketAudioSource: An error occurred in the receive loop: {e}")
        finally:
            print("WebSocketAudioSource: Receive loop finished.")
            if self.disconnect_callback:
                self.disconnect_callback()

    async def start(self):
        """
        Starts the task that listens for incoming audio messages.
        Note: This does not establish a connection, which must be done beforehand.
        """
        if self._receive_task is not None:
            print("WebSocketAudioSource: Receiver is already running.")
            return
        
        # Create a task to run the receive loop concurrently
        self._receive_task = asyncio.create_task(self._receive_loop())


    async def stop(self):
        """
        Stops the message receiving task gracefully.
        Note: This does NOT close the WebSocket connection itself.
        """
        if self._receive_task:
            print("WebSocketAudioSource: Stopping...")
            if not self._receive_task.done():
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass  # Cancellation is expected
            self._receive_task = None
            print("WebSocketAudioSource: Stopped.")
