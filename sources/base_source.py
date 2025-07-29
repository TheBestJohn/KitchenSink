
class BaseAudioSource:
    """
    Abstract base class for audio sources.

    An audio source is responsible for acquiring audio data from some origin
    (e.g., a network stream, a microphone) and forwarding it to a callable 'sink'.
    """

    def __init__(self, sink, disconnect_callback=None):
        """
        Initializes the BaseAudioSource.

        Args:
            sink (callable): A callable (function or method) that will receive the audio chunks.
                             It must accept one argument: a NumPy array of audio data.
            disconnect_callback (callable, optional): A callable that is invoked when the source
                                                     is disconnected or stops. Defaults to None.
        """
        if not callable(sink):
            raise TypeError("The sink must be a callable (e.g., a function or a method).")
        if disconnect_callback and not callable(disconnect_callback):
            raise TypeError("The disconnect_callback must be a callable or None.")
            
        self.sink = sink
        self.disconnect_callback = disconnect_callback

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
