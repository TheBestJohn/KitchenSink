
import asyncio
import numpy as np
import websockets
import json
import base64
from .base_source import BaseAudioSource

class TypedWebSocketServerAudioSource(BaseAudioSource):
    """
    An audio source that listens for a WebSocket client and handles typed JSON messages.
    It can process both audio streams and other message types like text or events.
    
    Expected message format (JSON string):
    {
        "type": "audio" | "text" | "custom_event",
        "payload": "..."
    }
    For "audio", the payload should be a Base64-encoded string of the raw audio bytes.
    """

    def __init__(self, sink, disconnect_callback=None, on_message_callback=None, host='0.0.0.0', port=8765, blocksize=None):
        """
        Initializes the TypedWebSocketServerAudioSource.

        Args:
            sink, disconnect_callback: Passed to BaseAudioSource.
            on_message_callback (callable, optional): A function to call for non-audio messages.
                                                     It receives two arguments: the message type (str) 
                                                     and the message payload (dict/str).
            host (str): The host address to listen on.
            port (int): The port to listen on.
            blocksize (int, optional): The preferred blocksize for audio chunks.
                                       Note: This source processes whatever it receives.
        """
        super().__init__(sink, disconnect_callback, blocksize=blocksize)
        self.on_message_callback = on_message_callback
        self.host = host
        self.port = port
        self.server = None
        self.server_task = None

    async def _handler(self, websocket, path):
        """Handles the WebSocket connection and message dispatching."""
        print(f"Typed WebSocket client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    payload = data.get("payload")

                    if msg_type == "audio":
                        # Decode the base64 audio data and push to the audio sink
                        audio_bytes = base64.b64decode(payload)
                        audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                        self.sink(audio_chunk)
                    else:
                        # For any other message type, use the generic callback
                        if self.on_message_callback:
                            try:
                                # Call the provided callback for custom handling
                                self.on_message_callback(msg_type, payload)
                            except Exception as e:
                                print(f"Error in on_message_callback: {e}")
                        else:
                            print(f"Received unhandled message type '{msg_type}' with no callback set.")

                except json.JSONDecodeError:
                    print(f"Warning: Received non-JSON message: {message[:100]}")
                except Exception as e:
                    print(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"Typed WebSocket client disconnected: {e}")
        finally:
            if self.disconnect_callback:
                self.disconnect_callback()

    async def start(self):
        """Starts the typed WebSocket server."""
        if self.server_task is not None:
            return
        print(f"Starting Typed WebSocket server on {self.host}:{self.port}")
        self.server = await websockets.serve(self._handler, self.host, self.port)
        self.server_task = asyncio.create_task(self.server.wait_closed())

    async def stop(self):
        """Stops the typed WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            self.server_task = None
            print("Typed WebSocket server stopped.")
