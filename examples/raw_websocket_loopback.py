
import asyncio
import sys
import os

# When the library is installed (e.g., with `pip install -e .`),
# the kitchensink package is available to be imported directly.
from kitchensink.sources.line_in_source import LineInAudioSource
from kitchensink.sinks.raw_websocket_audio_sink import RawWebSocketClientAudioSink
from kitchensink.sources.raw_websocket_audio_source import RawWebSocketServerAudioSource
from kitchensink.sinks.audio_player_sink import AudioPlayerSink
from kitchensink.utils import select_audio_device

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 8766 # Use a different port to avoid conflict with the typed example
WEBSOCKET_URI = f"ws://{HOST}:{PORT}"

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
# Use a smaller blocksize for lower latency, suitable for a loopback test
BLOCKSIZE = 480


async def main():
    """
    This example demonstrates a full audio pipeline using the RAW WebSocket components.
    It creates a loopback from a local microphone to local speakers, optimized for
    low-latency audio-only streaming.
    
    Pipeline:
    [LineInAudioSource] -> [RawWebSocketClientAudioSink] -> (Network) -> [RawWebSocketServerAudioSource] -> [AudioPlayerSink]
    """
    
    # --- Component Storage ---
    mic_source = None
    ws_client_sink = None
    ws_server_source = None
    speaker_sink = None

    print("--- Raw WebSocket Audio Loopback Example ---")
    print("This will capture audio from your microphone and play it back through your speakers.")
    
    try:
        # --- Sink Setup (Receiving End) ---
        print("\n--- Setting up receiving end (server -> speaker) ---")
        output_devices = AudioPlayerSink.list_output_devices()
        speaker_device = select_audio_device(output_devices, direction='output')
        
        # For a loopback test, it's ideal if the player sink's preferred blocksize
        # matches the source's blocksize.
        speaker_sink = AudioPlayerSink(
            sample_rate=SAMPLE_RATE, 
            channels=CHANNELS, 
            device=speaker_device,
            blocksize=BLOCKSIZE
        )
        await speaker_sink.start()

        # The WebSocket server will feed audio into the speaker sink
        ws_server_source = RawWebSocketServerAudioSource(
            sink=speaker_sink.push_chunk,
            disconnect_callback=speaker_sink.clear,
            host=HOST,
            port=PORT,
            blocksize=BLOCKSIZE
        )
        await ws_server_source.start()

        await asyncio.sleep(0.5)

        # --- Source Setup (Sending End) ---
        print("\n--- Setting up sending end (mic -> client) ---")
        input_devices = LineInAudioSource.list_input_devices()
        mic_device = select_audio_device(input_devices, direction='input')

        ws_client_sink = RawWebSocketClientAudioSink(uri=WEBSOCKET_URI, blocksize=BLOCKSIZE)
        await ws_client_sink.start()
        
        mic_source = LineInAudioSource(
            sink=ws_client_sink.push_chunk,
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCKSIZE,
            device=mic_device,
            disconnect_callback=ws_client_sink.close
        )
        await mic_source.start()
        
        print("\nAudio loopback is now active. Speak into your microphone.")
        print("Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except ConnectionRefusedError:
        print(f"\nFatal: WebSocket client could not connect to {WEBSOCKET_URI}.")
    except KeyboardInterrupt:
        print("\nStopping due to user interrupt...")
    except Exception as e:
        print(f"\nAn unexpected error occurred in main: {e}")
    finally:
        print("Shutting down all components...")
        if mic_source:
            await mic_source.stop()
        if ws_server_source:
            await ws_server_source.stop()
        print("Shutdown complete.")


if __name__ == "__main__":
    try:
        import websockets
    except ImportError:
        print("Error: The 'websockets' library is required to run this example.")
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
