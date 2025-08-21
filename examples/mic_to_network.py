
import asyncio
import sys
import os

# Add the project's root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from kitchensink.sources.line_in_source import LineInAudioSource
from kitchensink.sinks.network_audio_sink import TCPClientAudioSink
from kitchensink.utils import select_audio_device

# --- Configuration ---
# Server details (this should be the IP and Port of the machine running network_to_speaker.py)
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8123

# Audio settings (must match the settings on the server)
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
# This must match the `blocksize` on the server (network_to_speaker.py)
BLOCKSIZE = 480 # 480 frames * 2 bytes/frame = 960 bytes


async def main():
    """Main function to set up and run the source and sink."""
    line_source = None
    network_sink = None

    print("--- Local Microphone to Network Audio Forwarder ---")
    print(f"This will capture audio from your microphone and send it to {SERVER_HOST}:{SERVER_PORT}")
    
    try:
        # 1. Select the input device
        input_devices = LineInAudioSource.list_input_devices()
        selected_device = select_audio_device(input_devices, direction='input')

        # 2. Create the network sink, passing the blocksize for consistency
        network_sink = TCPClientAudioSink(
            host=SERVER_HOST,
            port=SERVER_PORT,
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=BLOCKSIZE
        )
        await network_sink.start()

        # 3. Create the line-in (microphone) source
        line_source = LineInAudioSource(
            sink=network_sink.push_chunk,
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCKSIZE,
            device=selected_device,
            disconnect_callback=network_sink.close # Close the sink when the source stops
        )

        # 3. Start the source
        await line_source.start()

        # 4. Keep the application running
        print("Audio forwarding is active. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)

    except ConnectionRefusedError:
        print(f"Fatal: Could not connect to the server at {SERVER_HOST}:{SERVER_PORT}.")
        print("Please ensure the 'network_to_speaker.py' example is running on the target machine.")
    except KeyboardInterrupt:
        print("\nStopping due to user interrupt...")
    except Exception as e:
        print(f"An unexpected error occurred in main: {e}")
    finally:
        print("Shutting down...")
        if line_source:
            await line_source.stop()
        # The source's disconnect_callback should handle closing the sink
        print("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
