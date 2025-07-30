
import collections
import threading

class BaseAudioSink:
    """
    Abstract base class for audio sinks.

    An audio sink is a destination for audio data. It takes audio chunks
    (as NumPy arrays) and performs an action, such as playing them through
    speakers, writing them to a file, or broadcasting them over a network.
    """

    def __init__(self, sample_rate=16000, channels=1, dtype='int16', blocksize=None):
        """
        Initializes the BaseAudioSink.

        Args:
            sample_rate (int): The sample rate of the audio (e.g., 16000 for speech).
            channels (int): The number of audio channels (e.g., 1 for mono).
            dtype (str): The data type of the audio samples (e.g., 'int16').
            blocksize (int, optional): The preferred number of frames per chunk
            for this sink. A source can use this to optimize the data flow.
            Defaults to None (no preference).
        """
        if dtype != 'int16':
            raise ValueError("Only 'int16' dtype is currently supported for sinks.")
        
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype
        self.blocksize = blocksize
        self._buffer = collections.deque()
        self._is_closed = threading.Event()

    async def start(self):
        """
        Optional method to initialize and start the sink.
        This is particularly important for sinks that need to perform asynchronous setup.
        This base implementation does nothing and can be overridden if needed.
        """
        pass

    def push_chunk(self, chunk):
        """
        Receives an audio chunk and adds it to the internal buffer for processing.
        This is the primary method used to feed data to the sink.
        
        Args:
            chunk (np.ndarray): A NumPy array containing the audio data for the chunk.
        """
        if self._is_closed.is_set():
            return
        self._buffer.append(chunk)

    def clear(self):
        """Clears any audio data currently held in the sink's internal buffer."""
        print(f"{self.__class__.__name__}: Clearing playout buffer.")
        self._buffer.clear()

    def close(self):
        """
        Signals the sink to gracefully stop its operations and clean up any resources.
        Sets an event that should be respected by any background processing loops.
        """
        self._is_closed.set()

    def __del__(self):
        """
        Ensures that the close method is called when the sink object is destroyed.
        Note: A well-behaved application should always explicitly call close().
        """
        self.close()
