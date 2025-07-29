
import pytest
import asyncio
import numpy as np

# Import the classes we want to test
from KitchenSink.sinks.base_sink import BaseAudioSink
from KitchenSink.sources.base_source import BaseAudioSource

# Since the factory pattern is used, we import the factory function directly.
# We will also import the specific classes to test their instantiation.
from KitchenSink.sinks.audio_player_sink import AudioPlayerSink, SoundDevicePlayer
from KitchenSink.sources.line_in_source import LineInAudioSource

# Marking all tests in this file to be run with asyncio
pytestmark = pytest.mark.asyncio


# --- Test Fixtures ---

@pytest.fixture
def mock_sink():
    """A simple mock sink that is just a list to capture pushed chunks."""
    return []

# --- Base Class Tests ---

async def test_base_source_requires_implementation():
    """Verify that the base source class cannot be used directly."""
    with pytest.raises(NotImplementedError):
        source = BaseAudioSource(sink=lambda x: None)
        await source.start()

    with pytest.raises(NotImplementedError):
        source = BaseAudioSource(sink=lambda x: None)
        await source.stop()

async def test_base_sink_requires_implementation():
    """Verify that the base sink class's start method is optional but can be abstract."""
    # The default start() does nothing, so this shouldn't raise an error
    sink = BaseAudioSink()
    await sink.start() 

# --- Instantiation Tests ---

def test_line_in_source_instantiation(mock_sink):
    """Test that LineInAudioSource can be created."""
    try:
        source = LineInAudioSource(sink=mock_sink.append)
        assert source is not None
        assert source.sink == mock_sink.append
    except Exception as e:
        pytest.fail(f"LineInAudioSource instantiation failed: {e}")

def test_audio_player_sink_instantiation():
    """Test that the AudioPlayerSink factory returns a valid player instance."""
    try:
        # We don't need to start it, just instantiate it
        sink = AudioPlayerSink()
        assert sink is not None
        # Check that it's an instance of one of the player classes
        # This test is a bit fragile if new players are added, but good for now.
        assert isinstance(sink, (SoundDevicePlayer)) # Add WinSdkPlayer if on Windows
    except Exception as e:
        # This can fail if no audio backend (sounddevice) is installed
        pytest.fail(f"AudioPlayerSink factory failed: {e}")

# --- Core Logic Tests ---

async def test_base_source_sink_communication():
    """
    Tests the fundamental interaction: a source pushing data to a sink.
    We create a dummy source and sink to test the push mechanism.
    """
    
    # Our mock sink is just a list
    received_chunks = []
    
    # Our mock source will have a method to simulate receiving data
    class DummySource(BaseAudioSource):
        def __init__(self, sink):
            super().__init__(sink)
        
        async def start(self):
            print("DummySource started")
        
        async def stop(self):
            print("DummySource stopped")

        # This is our test method
        def produce_chunk(self, chunk):
            self.sink(chunk)

    source = DummySource(sink=received_chunks.append)
    
    # Create a fake audio chunk
    test_chunk_1 = np.array([1, 2, 3], dtype=np.int16)
    test_chunk_2 = np.array([4, 5, 6], dtype=np.int16)

    # Simulate the source producing data
    source.produce_chunk(test_chunk_1)
    source.produce_chunk(test_chunk_2)

    # Assert that the sink received the data
    assert len(received_chunks) == 2
    assert np.array_equal(received_chunks[0], test_chunk_1)
    assert np.array_equal(received_chunks[1], test_chunk_2)

async def test_base_sink_buffer_logic():
    """Tests the buffering and clearing logic of the BaseAudioSink."""
    sink = BaseAudioSink()
    
    test_chunk = np.array([1, 1, 1], dtype=np.int16)
    
    # The internal buffer should be a deque
    assert hasattr(sink, '_buffer')
    assert len(sink._buffer) == 0

    # Test pushing a chunk
    sink.push_chunk(test_chunk)
    assert len(sink._buffer) == 1
    
    # Test clearing the buffer
    sink.clear()
    assert len(sink._buffer) == 0

    # Test closing
    assert not sink._is_closed.is_set()
    sink.close()
    assert sink._is_closed.is_set()
