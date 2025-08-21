import asyncio
import sys
import os

# When the library is installed (e.g., with `pip install -e .`),
# the kitchensink package is available to be imported directly.
from kitchensink.sources.network_audio_source import TCPServerAudioSource
from kitchensink.sinks.audio_player_sink import AudioPlayerSink
from kitchensink.utils import select_audio_device


async def main():
    """Main function to set up and run the source and sink."""
    player_sink = None
    audio_source = None
    try:
        # --- Configuration ---
        SAMPLE_RATE = 16000
        CHANNELS = 1
        GAIN_FACTOR = 2.5
        PORT = 8123

        # 1. Select and create the sink
        output_devices = AudioPlayerSink.list_output_devices()
        selected_device = select_audio_device(output_devices, direction='output')
        
        player_sink = AudioPlayerSink(sample_rate=SAMPLE_RATE, channels=CHANNELS, device=selected_device)
        await player_sink.start()

        # 2. Create the audio source, providing the sink's methods
        audio_source = TCPServerAudioSource(
            sink=player_sink.push_chunk,
            disconnect_callback=player_sink.clear,
            port=PORT,
            gain_factor=GAIN_FACTOR,
            blocksize=480  # 480 frames * 2 bytes/frame = 960 bytes
        )

        # 3. Start the source server
        print("Starting TCP audio source server...")
        await audio_source.start()

    except KeyboardInterrupt:
        print("\nServer stopping due to user interrupt...")
    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        if audio_source:
            await audio_source.stop()
        if player_sink:
            player_sink.close()
        print("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
