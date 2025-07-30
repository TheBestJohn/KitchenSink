
import asyncio
import sys
import os

# When the library is installed (e.g., with `pip install -e .`),
# the kitchensink package is available to be imported directly.
from kitchensink.sources.line_in_source import LineInAudioSource
from kitchensink.sinks.typed_websocket_audio_sink import TypedWebSocketClientAudioSink
from kitchensink.sources.typed_websocket_audio_source import TypedWebSocketServerAudioSource
from kitchensink.sinks.audio_player_sink import AudioPlayerSink
from kitchensink.utils import select_audio_device

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 8765
WEBSOCKET_URI = f"ws://{HOST}:{PORT}"

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
CHUNK_SIZE = 1024


async def main():
    """
    This example demonstrates a full audio pipeline using the TYPED WebSocket components.
    It creates a loopback from a local microphone to local speakers, and also sends
    a text message upon connection to demonstrate multi-message capability.
    
    Pipeline:
    [LineInAudioSource] -> [TypedWebSocketClientAudioSink] -> (Network) -> [TypedWebSocketServerAudioSource] -> [AudioPlayerSink]
    """
    
    # --- Component Storage ---
    mic_source = None
    ws_client_sink = None
    ws_server_source = None
    speaker_sink = None

    print("--- Typed WebSocket Audio Loopback Example ---")
    print("This will capture audio from your microphone and play it back through your speakers.")
    print("You should hear your own voice with a slight delay.")
    
    try:
        # --- Sink Setup (Receiving End) ---
        print("\n--- Setting up receiving end (server -> speaker) ---")
        output_devices = AudioPlayerSink.list_output_devices()
        speaker_device = select_audio_device(output_devices, direction='output')
        
        speaker_sink = AudioPlayerSink(sample_rate=SAMPLE_RATE, channels=CHANNELS, device=speaker_device)
        await speaker_sink.start()

        # Define a callback for the server to handle non-audio messages
        def handle_server_message(msg_type, payload):
            print(f"[Server] Received message! Type: '{msg_type}', Payload: {payload}")

        # The WebSocket server will feed audio into the speaker sink
        ws_server_source = TypedWebSocketServerAudioSource(
            sink=speaker_sink.push_chunk,
            disconnect_callback=speaker_sink.clear,
            on_message_callback=handle_server_message,
            host=HOST,
            port=PORT
        )
        await ws_server_source.start()

        # Give the server a moment to start up
        await asyncio.sleep(0.5)

        # --- Source Setup (Sending End) ---
        print("\n--- Setting up sending end (mic -> client) ---")
        input_devices = LineInAudioSource.list_input_devices()
        mic_device = select_audio_device(input_devices, direction='input')

        # The WebSocket client sink will send data it receives from the mic
        ws_client_sink = TypedWebSocketClientAudioSink(uri=WEBSOCKET_URI)
        await ws_client_sink.start()

        # --- Demonstrate Sending a Non-Audio Message ---
        print("[Client] Sending a 'hello' text message...")
        await ws_client_sink.send_message("text", "Hello from the client!")
        
        mic_source = LineInAudioSource(
            sink=ws_client_sink.push_chunk, # The sink handles encoding the audio
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            chunk_size=CHUNK_SIZE,
            device=mic_device,
            disconnect_callback=ws_client_sink.close # If mic stops, close the client
        )
        await mic_source.start()
        
        print("\nAudio loopback is now active. Speak into your microphone.")
        print("Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except ConnectionRefusedError:
        print(f"\nFatal: WebSocket client could not connect to {WEBSOCKET_URI}.")
        print("This can happen if the server part of the script failed to start.")
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
        
        # Sinks are closed by the disconnect callbacks of the sources
        print("Shutdown complete.")


if __name__ == "__main__":
    # Add the websockets dependency check
    try:
        import websockets
    except ImportError:
        print("Error: The 'websockets' library is required to run this example.")
        print("Please install it with: pip install websockets")
        # Or install the library with the optional extra: pip install .[websockets]
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
