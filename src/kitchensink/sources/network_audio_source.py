import asyncio
import numpy as np
from .base_source import BaseAudioSource

class TCPServerAudioSource(BaseAudioSource):
    """
    An audio source that listens for a single incoming TCP connection,
    receives audio data, processes it, and pushes it to a provided sink.
    """

    def __init__(self, sink, disconnect_callback=None, host='0.0.0.0', port=8123, gain_factor=1.0, blocksize=960):
        """
        Initializes the TCPServerAudioSource.

        Args:
            sink: A callable that accepts one argument (the audio chunk as a NumPy array).
            disconnect_callback (callable, optional): A callable that is invoked when a client disconnects.
            host (str): The host address to listen on.
            port (int): The port to listen on.
            gain_factor (float): Factor to amplify the incoming audio.
            blocksize (int): The number of frames per audio chunk.
        """
        super().__init__(sink, disconnect_callback, blocksize=blocksize)
        self.host = host
        self.port = port
        self.gain_factor = gain_factor
        self.server = None

    async def _handle_client(self, reader, writer):
        """Handles a single client connection."""
        addr = writer.get_extra_info('peername')
        print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")

        # Each int16 frame is 2 bytes
        chunk_bytes = self.blocksize * 2

        try:
            while True:
                try:
                    data = await reader.readexactly(chunk_bytes)
                    if not data:
                        break # Should not happen with readexactly, but good practice
                except (asyncio.IncompleteReadError, ConnectionAbortedError, ConnectionResetError) as e:
                    print(f"Client {addr} disconnected: {e}")
                    break # Exit the loop cleanly on disconnection

                audio_chunk = np.frombuffer(data, dtype=np.int16)

                if self.gain_factor != 1.0:
                    amplified_chunk = (audio_chunk.astype(np.float32) * self.gain_factor)
                    processed_chunk = np.clip(amplified_chunk, -32768, 32767).astype(np.int16)
                else:
                    processed_chunk = audio_chunk

                self.sink(processed_chunk)

        except Exception as e:
            print(f"An unexpected error occurred with client {addr}: {e}")
        finally:
            print(f"Closing connection from {addr}")
            if self.disconnect_callback:
                try:
                    self.disconnect_callback()
                except Exception as e:
                    print(f"Error in disconnect_callback: {e}")
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Starts the server to listen for an audio source."""
        if self.server is not None:
            print("Server is already running.")
            return

        self.server = await asyncio.start_server(
            self._handle_client, self.host, self.port)

        addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
        print(f'[*] Audio source server listening on {addrs}')

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stops the audio server gracefully."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            print("Server stopped.")
