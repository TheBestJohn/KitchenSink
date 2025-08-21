
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

    def __init__(self, sink, disconnect_callback=None, sample_rate=None, channels=None, dtype='int16', blocksize=1024, device=None):
        """
        Initializes the LineInAudioSource.

        Args:
            sink, disconnect_callback: Passed to BaseAudioSource.
            sample_rate (int, optional): The desired sample rate. If None, the device's default is used.
            channels (int, optional): The desired number of channels. If None, defaults to 1.
            dtype (str): The data type of the audio.
            blocksize (int): The number of frames per chunk to read from the microphone.
            device (str or int, optional): The input device to use. If None, it checks the
                                           KS_INPUT_DEVICE env var, otherwise uses the system default.
        """
        self.device = device or os.environ.get("KS_INPUT_DEVICE")

        # Query device information to determine the actual settings to use
        try:
            device_info = sd.query_devices(self.device, 'input')
        except ValueError:
            print(f"Warning: Input device '{self.device}' not found. Using default device.")
            self.device = None
            device_info = sd.query_devices(self.device, 'input')

        # Determine the final audio parameters based on user preference and device capability
        final_samplerate = sample_rate or int(device_info['default_samplerate'])
        
        max_channels = device_info['max_input_channels']
        final_channels = channels or 1
        if final_channels > max_channels:
            print(f"Warning: Requested {final_channels} channels, but device only supports {max_channels}. Clamping to {max_channels}.")
            final_channels = max_channels

        # Initialize the base class with the determined (actual) audio parameters
        super().__init__(
            sink,
            sample_rate=final_samplerate,
            channels=final_channels,
            dtype=dtype,
            disconnect_callback=disconnect_callback,
            blocksize=blocksize
        )

        # The stream and thread for capturing audio
        self._stream = None
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._loop = None

    def _audio_callback(self, indata, frames, time, status):
        """This function is called by sounddevice for each new audio chunk."""
        if status:
            print(f"LineInAudioSource: Status from sounddevice: {status}")
        
        # Since push_chunk is now async, we must schedule it on the event
        # loop from this thread using run_coroutine_threadsafe.
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.sink(indata.copy()), self._loop)
            try:
                # We add a short timeout. If backpressure is too high, we'd rather
                # drop a chunk than block the high-priority audio thread.
                future.result(timeout=0.05)
            except asyncio.TimeoutError:
                print("LineInAudioSource: Sink is busy, dropping a chunk.")
            except Exception as e:
                print(f"LineInAudioSource: Error calling sink: {e}")

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
                blocksize=self.blocksize,
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
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                print("LineInAudioSource: Error: Cannot start without a running asyncio event loop.")
                return

            self._stop_event.clear()
            self._thread.start()
        else:
            print("LineInAudioSource: Capture is already running.")

    async def stop(self):
        """Stops the microphone capture thread gracefully."""
        print("LineInAudioSource: Stopping audio capture...")
        self._stop_event.set()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"LineInAudioSource: Error during explicit stream stop: {e}")

        if self._thread.is_alive():
            try:
                loop = asyncio.get_running_loop()
                # Run the blocking join in an executor to avoid blocking the event loop
                await loop.run_in_executor(None, self._thread.join, 2)
            except RuntimeError:
                # Fallback for when the event loop is not running
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
