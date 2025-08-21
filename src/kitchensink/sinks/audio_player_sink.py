import collections
import sys
import numpy as np
import os
import platform
import asyncio
import threading
import time
from .base_sink import BaseAudioSink

# --- SoundDevice Implementation (Default Fallback) ---
try:
    import sounddevice as sd
    _sounddevice_available = True
except (ImportError, OSError):
    print("Warning: sounddevice library not found or could not be initialized.")
    _sounddevice_available = False

if _sounddevice_available:
    class SoundDevicePlayer(BaseAudioSink):
        """A sink that plays audio using the ``sounddevice`` library.

        This is the default fallback player for non-Windows systems or when the
        ``winsdk`` is not installed.
        """
        def __init__(self, *args, device, **kwargs):
            super().__init__(*args, **kwargs)
            self.device = device
            self._stream = None
            self._frame_offset = 0 # Tracks our position in the current chunk

        async def start(self):
            """Initializes and starts the ``sounddevice`` output stream."""
            device_info = f" on device '{self.device.get('name')}'" if self.device else " on default device"
            print(f"SoundDevicePlayer: Starting audio stream{device_info}.")
            device_index = self.device.get('index')
            self._stream = sd.OutputStream(
                device=device_index,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                callback=self._audio_callback,
                latency='low'
            )
            self._stream.start()

        def _audio_callback(self, outdata, frames, time, status):
            """
            This callback is the heart of the audio playback. It fills the
            `outdata` buffer with exactly `frames` number of samples, handling
            chunk boundaries and buffer underruns gracefully.
            """
            if status:
                print(f"SoundDevicePlayer Status: {status}", file=sys.stderr)

            remaining_frames = frames
            out_offset = 0

            while remaining_frames > 0:
                if not self._buffer:
                    # Buffer is empty, fill the rest of outdata with silence
                    outdata[out_offset:, :] = 0
                    return

                # Get the current chunk from the front of the deque
                current_chunk = self._buffer[0]
                
                # Calculate how many frames are left in the current chunk
                frames_in_chunk = len(current_chunk) - self._frame_offset
                
                # Determine how many frames to copy in this iteration
                frames_to_copy = min(remaining_frames, frames_in_chunk)
                
                # Copy the data
                end_offset = self._frame_offset + frames_to_copy
                # Ensure the data is correctly shaped for assignment
                outdata[out_offset : out_offset + frames_to_copy, :] = current_chunk[self._frame_offset : end_offset].reshape(-1, self._channels)

                # Update our offsets and remaining counts
                self._frame_offset += frames_to_copy
                out_offset += frames_to_copy
                remaining_frames -= frames_to_copy

                # If we've finished with the current chunk, remove it from the deque
                if self._frame_offset >= len(current_chunk):
                    self._buffer.popleft()
                    self._frame_offset = 0
        
        def clear(self):
            """Clears the buffer and resets the frame offset."""
            super().clear()
            self._frame_offset = 0

        def close(self):
            super().close()
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                print("SoundDevicePlayer stream closed.")

        @staticmethod
        def list_output_devices():
            """Lists available audio output devices using ``sounddevice``.

            Returns:
                list: A list of device dictionaries from ``sounddevice``.
            """
            try:
                devices = sd.query_devices()
                return [d for d in devices if d.get('max_output_channels', 0) > 0]
            except Exception as e:
                print(f"Could not query audio devices: {e}")
                return []

# --- Windows WinSDK Implementation ---
_winsdk_available = False
if platform.system() == "Windows":
    try:
        import winsdk.windows.media as wmedia
        import winsdk.windows.media.audio as wma
        import winsdk.windows.media.mediaproperties as wmp
        from winsdk.windows.foundation import IMemoryBufferByteAccess
        import ctypes
        from comtypes import IUnknown, cast, POINTER
        _winsdk_available = True
    except ImportError:
        print("Warning: winsdk library not found. Falling back to sounddevice.")
        _winsdk_available = False

if _winsdk_available:
    class MemoryBufferByteAccess(IUnknown):
        _com_interfaces_ = [IMemoryBufferByteAccess]
        _iid_ = IMemoryBufferByteAccess

    class WinSdkPlayer(BaseAudioSink):
        """A sink that plays audio using the Windows SDK (WASAPI) for low latency.

        This player is only available on Windows and when the ``winsdk`` package
        is installed. It does not currently support selecting a specific output
        device; it will always use the system default media device.
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._graph = None
            self._frame_input_node = None
            self._playback_thread = None

        async def start(self):
            print("WinSdkPlayer: Initializing audio graph...")
            settings = wma.AudioGraphSettings(wma.AudioRenderCategory.MEDIA)
            create_graph_result = await wma.AudioGraph.create_async(settings)
            if create_graph_result.status != wma.AudioGraphCreationStatus.SUCCESS:
                raise RuntimeError(f"Failed to create AudioGraph: {create_graph_result.status}")
            self._graph = create_graph_result.graph
            output_node_result = await self._graph.create_device_output_node_async()
            if output_node_result.status != wma.AudioDeviceNodeCreationStatus.SUCCESS:
                raise RuntimeError("Failed to create device output node.")
            encoding_props = self._graph.encoding_properties
            encoding_props.sample_rate = self._sample_rate
            encoding_props.channel_count = self._channels
            encoding_props.bits_per_sample = 16
            self._frame_input_node = self._graph.create_frame_input_node(encoding_props)
            self._frame_input_node.add_outgoing_connection(output_node_result.device_output_node)
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
            self._graph.start()
            print("WinSdkPlayer: Audio graph started.")

        def _playback_loop(self):
            while not self._is_closed.is_set():
                try:
                    chunk = self._buffer.popleft()
                    self._submit_chunk(chunk)
                except IndexError:
                    time.sleep(0.005)
            print("WinSdkPlayer: Playback loop finished.")

        def _submit_chunk(self, chunk: np.ndarray):
            num_bytes = chunk.nbytes
            frame = wmedia.AudioFrame(num_bytes)
            with frame.lock_buffer(wmedia.AudioBufferAccessMode.WRITE) as audio_buffer:
                byte_access = cast(audio_buffer, POINTER(MemoryBufferByteAccess))
                buffer_ptr, _ = byte_access.get_buffer()
                ctypes.memmove(buffer_ptr, chunk.ctypes.data, num_bytes)
            self._frame_input_node.add_frame(frame)

        def close(self):
            super().close()
            print("WinSdkPlayer: Closing audio graph...")
            if self._playback_thread and self._playback_thread.is_alive():
                self._playback_thread.join(timeout=1)
            if self._graph:
                self._graph.stop()
                self._graph.close()
                self._graph = None
            print("WinSdkPlayer: Audio graph closed.")

# --- Factory Class ---
def AudioPlayerSink(*args, device=None, **kwargs):
    """Factory that selects the best available audio player for the current OS.

    Args:
        device (str or int, optional): The output device identifier. If ``None``,
            the ``KS_OUTPUT_DEVICE`` environment variable is checked before
            falling back to the system default. This only applies to the
            ``SoundDevicePlayer``.
        *args: Positional arguments for the player's constructor.
        **kwargs: Keyword arguments for the player's constructor.
    """
    final_device = device or os.environ.get("KS_OUTPUT_DEVICE")

    if platform.system() == "Windows" and _winsdk_available:
        print("Selected WinSdkPlayer for audio output.")
        return WinSdkPlayer(*args, **kwargs)
    
    if _sounddevice_available:
        print("Selected SoundDevicePlayer for audio output.")
        return SoundDevicePlayer(*args, device=final_device, **kwargs)

    raise RuntimeError("No suitable audio playback library found. Please install 'sounddevice' or 'winsdk'.")

if _sounddevice_available:
    AudioPlayerSink.list_output_devices = SoundDevicePlayer.list_output_devices
else:
    AudioPlayerSink.list_output_devices = lambda: []
