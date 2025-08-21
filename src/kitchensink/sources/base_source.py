
import numpy as np
from scipy.signal import resample


class BaseAudioSource:
    """
    Abstract base class for audio sources.

    An audio source is responsible for acquiring audio data from some origin
    (e.g., a network stream, a microphone) and forwarding it to a callable 'sink'.
    """

    def __init__(self, sink, sample_rate=16000, channels=1, dtype='int16', disconnect_callback=None, blocksize=None):
        """
        Initializes the BaseAudioSource.

        Args:
            sink (callable): A callable (function or method) that will receive the audio chunks.
                             It must accept one argument: a NumPy array of audio data.
            sample_rate (int): The native sample rate of the audio from the source.
            channels (int): The native number of channels from the source.
            dtype (str or numpy.dtype): The native data type of the audio from the source.
            disconnect_callback (callable, optional): A callable that is invoked when the source
                                                     is disconnected or stops. Defaults to None.
            blocksize (int, optional): The number of frames per chunk for the
                source to generate. If ``None``, the source may attempt to use the
                sink's preferred blocksize.
        """
        if not callable(sink):
            raise TypeError("The sink must be a callable (e.g., a function or a method).")
        if disconnect_callback and not callable(disconnect_callback):
            raise TypeError("The disconnect_callback must be a callable or None.")

        self._original_sink = sink
        self.sink = sink
        self.disconnect_callback = disconnect_callback
        self.blocksize = blocksize

        # Store the native format of the source
        self._source_sample_rate = sample_rate
        self._source_channels = channels
        self._source_dtype = np.dtype(dtype)

        # Public properties reflect the *output* format, which can be changed by convert_output
        self.sample_rate = self._source_sample_rate
        self.channels = self._source_channels
        self.dtype = self._source_dtype
        self._is_converting = False

    def convert_output(self, target_sample_rate, target_dtype, target_channels=None):
        """
        Wraps the sink to automatically convert audio chunks to a different
        sample rate, data type, and/or channel count.

        Args:
            target_sample_rate (int): The desired output sample rate.
            target_dtype (str or numpy.dtype): The desired output data type.
            target_channels (int, optional): The desired output channel count.
        """
        target_dtype = np.dtype(target_dtype)
        target_channels = target_channels or self._source_channels

        # Check if any conversion is actually needed
        needs_resampling = self._source_sample_rate != target_sample_rate
        needs_dtype_conversion = self._source_dtype != target_dtype
        needs_channel_conversion = self._source_channels != target_channels

        if not any([needs_resampling, needs_dtype_conversion, needs_channel_conversion]):
            self.sink = self._original_sink
            self.sample_rate = self._source_sample_rate
            self.dtype = self._source_dtype
            self.channels = self._source_channels
            self._is_converting = False
            return

        self._is_converting = True

        async def conversion_wrapper(chunk):
            # --- Robust Audio Conversion Pipeline ---

            # 1. Normalize source audio to a standard float32 workspace format
            workspace_chunk = chunk
            if np.issubdtype(chunk.dtype, np.integer):
                i_info = np.iinfo(chunk.dtype)
                workspace_chunk = chunk.astype(np.float32) / (i_info.max + 1)
            elif chunk.dtype != np.float32:
                # For other float types, just convert
                workspace_chunk = chunk.astype(np.float32)

            # 2. Resample (if needed) on the normalized float data
            if needs_resampling:
                num_samples = int(len(workspace_chunk) * target_sample_rate / self._source_sample_rate)
                if num_samples > 0:
                    from scipy.signal import resample
                    workspace_chunk = resample(workspace_chunk, num_samples)
                else:
                    workspace_chunk = np.array([], dtype=np.float32)
            
            # 3. Convert channels (if needed) on the resampled float data
            if needs_channel_conversion:
                if self._source_channels == 1 and target_channels == 2:
                    workspace_chunk = np.stack([workspace_chunk, workspace_chunk], axis=-1)
                elif self._source_channels == 2 and target_channels == 1:
                    workspace_chunk = workspace_chunk.mean(axis=1)
                else:
                    print(f"Warning: Channel conversion from {self._source_channels} to {target_channels} is not fully supported.")

            # 4. Convert the final workspace chunk to the target data type
            final_chunk = workspace_chunk
            if np.issubdtype(target_dtype, np.integer):
                i_info = np.iinfo(target_dtype)
                final_chunk = (workspace_chunk * i_info.max).astype(target_dtype)
            elif target_dtype != np.float32:
                final_chunk = workspace_chunk.astype(target_dtype)

            # 5. Call the original sink with the fully converted chunk
            if final_chunk.size > 0:
                await self._original_sink(final_chunk)

        self.sink = conversion_wrapper
        self.sample_rate = target_sample_rate
        self.dtype = target_dtype
        self.channels = target_channels
    async def start(self):
        """
        Starts the audio source. This method should handle any setup required,
        begin acquiring audio, and continue until stop() is called or the source ends.
        """
        raise NotImplementedError("Each audio source must implement its own start method.")

    async def stop(self):
        """
        Signals the audio source to gracefully stop acquiring audio and clean up resources.
        """
        raise NotImplementedError("Each audio source must implement its own stop method.")

    def __del__(self):
        """
        Ensures that resources are cleaned up if the source is garbage collected.
        Note: A well-behaved application should always explicitly call stop().
        """
        # This is a fallback. Explicitly calling stop() is always preferred.
        # Since stop is async, we can't reliably call it here.
        # This highlights the importance of manual resource management in async contexts.
        pass
