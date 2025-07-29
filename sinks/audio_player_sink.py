
import collections
import sys
import numpy as np
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
        """A sink that plays audio using sounddevice."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._stream = None

        async def start(self):
            print("SoundDevicePlayer: Starting audio stream.")
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                callback=self._audio_callback,
                latency='low'
            )
            self._stream.start()

        def _audio_callback(self, outdata, frames, time, status):
            if status:
                print(status, file=sys.stderr)
            try:
                data = self._buffer.popleft()
                outdata[:] = data.reshape(-1, self._channels)
            except IndexError:
                outdata.fill(0)

        def close(self):
            super().close()
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                print("SoundDevicePlayer stream closed.")

# --- Windows WinSDK Implementation ---
_winsdk_available = False
if platform.system() == "Windows":
    try:
        import winsdk.windows.media as wmedia
        import winsdk.windows.media.audio as wma
        import winsdk.windows.media.mediaproperties as wmp
        from winsdk.windows.foundation import IMemoryBufferByteAccess
        import ctypes
        _winsdk_available = True
    except ImportError:
        print("Warning: winsdk library not found. Falling back to sounddevice.")
        print("         For optimal performance on Windows, please run: pip install winsdk")
        _winsdk_available = False

if _winsdk_available:
    # This is a bit of COM magic to get the raw pointer to the buffer
    from comtypes import IUnknown, cast, POINTER
    class MemoryBufferByteAccess(IUnknown):
        _com_interfaces_ = [IMemoryBufferByteAccess]
        _iid_ = IMemoryBufferByteAccess

    class WinSdkPlayer(BaseAudioSink):
        """A sink that plays audio using the Windows SDK (WASAPI)."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._graph = None
            self._frame_input_node = None
            self._playback_thread = None

        async def start(self):
            print("WinSdkPlayer: Initializing audio graph...")
            settings = wma.AudioGraphSettings(wma.AudioRenderCategory.MEDIA)
            settings.primary_render_device = await wma.DeviceInformation.create_for_audio_rendering_category_async(wma.AudioRenderCategory.MEDIA)
            
            create_graph_result = await wma.AudioGraph.create_async(settings)
            if create_graph_result.status != wma.AudioGraphCreationStatus.SUCCESS:
                raise RuntimeError(f"Failed to create AudioGraph: {create_graph_result.status}")
            self._graph = create_graph_result.graph

            output_node_result = await self._graph.create_device_output_node_async()
            if output_node_result.status != wma.AudioDeviceNodeCreationStatus.SUCCESS:
                raise RuntimeError("Failed to create device output node.")

            encoding_props = wmp.AudioEncodingProperties()
            encoding_props.sample_rate = self._sample_rate
            encoding_props.channel_count = self._channels
            encoding_props.bits_per_sample = 16
            encoding_props.subtype = "PCM"
            
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
                    time.sleep(0.005) # Wait for more data
                except Exception as e:
                    print(f"Error in WinSdkPlayer playback loop: {e}", file=sys.stderr)
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
def AudioPlayerSink(*args, **kwargs):
    """
    Factory function that returns the best available audio player for the current platform.
    
    On Windows, it prioritizes the `WinSdkPlayer` for lower latency.
    On other platforms or if WinSDK is not installed, it uses `SoundDevicePlayer`.
    """
    if platform.system() == "Windows" and _winsdk_available:
        # Note: WinSdkPlayer uses the system default device, so device listing is a SoundDevice feature.
        print("Selected WinSdkPlayer for audio output.")
        return WinSdkPlayer(*args, **kwargs)
    
    if _sounddevice_available:
        print("Selected SoundDevicePlayer for audio output.")
        return SoundDevicePlayer(*args, **kwargs)

    raise RuntimeError("No suitable audio playback library found. Please install 'sounddevice' or 'winsdk'.")

# Attach the static device listing method to the factory function itself
# so it can be called like a class method, e.g., AudioPlayerSink.list_output_devices()
if _sounddevice_available:
    AudioPlayerSink.list_output_devices = SoundDevicePlayer.list_output_devices
else:
    # If sounddevice is not available, provide a dummy method to avoid errors
    AudioPlayerSink.list_output_devices = lambda: []
