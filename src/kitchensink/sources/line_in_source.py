
import asyncio
import sounddevice as sd
import numpy as np
import threading
import os
from .base_source import BaseAudioSource

class LineInAudioSource(BaseAudioSource):
    """
    An audio source that captures audio from a local line-in/microphone.
    """

    def __init__(self, sink, disconnect_callback=None, sample_rate=16000, channels=1, dtype='int16', chunk_size=1024, device=None):
        """
        Initializes the LineInAudioSource.

        Args:
            sink, disconnect_callback: Passed to BaseAudioSource.
            sample_rate (int): The sample rate for capturing audio.
            channels (int): The number of channels for capturing audio.
            dtype (str): The data type of the audio.
            chunk_size (int): The number of frames per chunk to read from the microphone.
            device (str or int, optional): The input device to use. If None, it checks the
                                           KS_INPUT_DEVICE env var, otherwise uses the system default.
        """
        super().__init__(sink, disconnect_callback)
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.chunk_size = chunk_size
        self.device = device or os.environ.get("KS_INPUT_DEVICE")
        self._stream = None
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)

    def _audio_callback(self, indata, frames, time, status):
        """This function is called by sounddevice for each new audio chunk."""
        if status:
            print(f"LineInAudioSource: Status from sounddevice: {status}")
        # The sink expects a numpy array
        self.sink(indata.copy())

    def _capture_loop(self):
        """The main loop for the audio capture thread."""
        device_info = f" on device '{self.device}'" if self.device else ""
        print(f"LineInAudioSource: Starting audio capture{device_info}.")
        try:
            self._stream = sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=self._audio_callback
            )
            with self._stream:
                self._stop_event.wait()
        except Exception as e:
            print(f"LineInAudioSource: An error occurred in the capture thread: {e}")
        finally:
            print("LineInAudioSource: Audio capture stopped.")
            if self.disconnect_callback:
                self.disconnect_callback()

    async def start(self):
        """Starts the microphone capture thread."""
        if not self._thread.is_alive():
            self._stop_event.clear()
            self._thread.start()
        else:
            print("LineInAudioSource: Capture is already running.")

    async def stop(self):
        """Stops the microphone capture thread."""
        print("LineInAudioSource: Stopping audio capture...")
        self._stop_event.set()
        if self._stream:
            # Although the stream is managed by the context manager in the thread,
            # an explicit stop can be good practice.
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"LineInAudioSource: Error during explicit stream stop: {e}")

        if self._thread.is_alive():
            self._thread.join(timeout=2)
        print("LineInAudioSource: Capture stopped.")

    @staticmethod
    def list_input_devices():
        """Static method to list available audio input devices."""
        try:
            devices = sd.query_devices()
            # Filter for devices with at least one input channel
            return [device for device in devices if device.get('max_input_channels', 0) > 0]
        except Exception as e:
            print(f"Could not query audio devices: {e}")
            return []
