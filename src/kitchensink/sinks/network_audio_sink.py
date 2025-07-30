
import asyncio
import numpy as np
import threading
import time
from .base_sink import BaseAudioSink

class TCPClientAudioSink(BaseAudioSink):
    """
    An audio sink that connects to a TCP server and sends audio chunks.
    """

    def __init__(self, host, port, sample_rate=16000, channels=1, dtype='int16', blocksize=None):
        """
        Initializes the TCPClientAudioSink.

        Args:
            host (str): The hostname or IP address of the server to connect to.
            port (int): The port of the server.
            sample_rate, channels, dtype, blocksize: Passed to BaseAudioSink.
        """
        super().__init__(sample_rate, channels, dtype, blocksize)
        self.host = host
        self.port = port
        self._writer = None
        self._loop = None
        self._send_thread = threading.Thread(target=self._send_loop, daemon=True)

    async def start(self):
        """
        Establishes the connection to the TCP server and starts the sending loop.
        """
        print(f"TCPClientAudioSink: Attempting to connect to {self.host}:{self.port}...")
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            self._writer = writer
            self._loop = asyncio.get_running_loop()
            self._send_thread.start()
            print("TCPClientAudioSink: Connection successful.")
        except ConnectionRefusedError:
            print(f"TCPClientAudioSink: Connection refused by {self.host}:{self.port}. Is the server running?")
            self.close()
            raise
        except Exception as e:
            print(f"TCPClientAudioSink: An unexpected error occurred during connection: {e}")
            self.close()
            raise
    
    def _send_loop(self):
        """The actual sending logic that runs in a separate thread."""
        while not self._is_closed.is_set():
            try:
                chunk = self._buffer.popleft()
                if self._writer and not self._writer.is_closing():
                    # Schedule the write operation on the event loop from this thread
                    future = asyncio.run_coroutine_threadsafe(self._write_chunk(chunk), self._loop)
                    # Wait for the result to ensure the chunk is sent before proceeding
                    future.result() 
            except IndexError:
                time.sleep(0.005) # Wait for more data
            except Exception as e:
                print(f"TCPClientAudioSink: Error in send loop: {e}")
                self.close()

    async def _write_chunk(self, chunk: np.ndarray):
        """Coroutine to write a chunk to the stream."""
        self._writer.write(chunk.tobytes())
        await self._writer.drain()

    def close(self):
        """Closes the connection and stops the sender thread."""
        if not self._is_closed.is_set():
            super().close()
            print("TCPClientAudioSink: Closing connection...")
            if self._writer:
                # Schedule the closing on the event loop
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._writer.close(), self._loop)
                else:
                    # If loop is not running, a simple close might be all we can do
                    try:
                        self._writer.close()
                    except: # Ignore errors on final close
                        pass
            
            if self._send_thread.is_alive():
                self._send_thread.join(timeout=1)
            print("TCPClientAudioSink: Connection closed.")
