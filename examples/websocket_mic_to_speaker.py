"""
This example demonstrates a full duplex audio connection between a client and a
server using the decoupled WebSocket audio components.

It showcases how to use WebSocketAudioSource and WebSocketAudioSink as generic
"handlers" for sending and receiving audio over a connection that is managed
separately by a client or server implementation.

Usage:
1. Start the server in one terminal:
   python examples/websocket_mic_to_speaker.py server

2. Start the client in another terminal:
   python examples/websocket_mic_to_speaker.py client

The server will capture audio from the default microphone and send it to the
client. The client will receive the audio and play it on the default speaker.
"""

import asyncio
import argparse
import websockets
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kitchensink.sources.line_in_source import LineInAudioSource
from kitchensink.sinks.audio_player_sink import AudioPlayerSink
from kitchensink.sources.websocket_audio_source import WebSocketAudioSource
from kitchensink.sinks.websocket_audio_sink import WebSocketAudioSink
from kitchensink.utils import select_audio_device

HOST = 'localhost'
PORT = 8765
URI = f"ws://{HOST}:{PORT}"

# --- Server Implementation ---

async def server_handler(websocket, path=None):
    """
    Handles a single client connection on the server.
    - Creates a LineInAudioSource to capture microphone audio.
    - Creates a WebSocketAudioSink to send the captured audio to the client.
    - Wires them together and runs until the client disconnects.
    """
    print(f"Server: Client connected from {websocket.remote_address}")
    line_in = None
    ws_sink = None
    try:
        # --- Handshake Step 1: Wait for the client's request ---
        message = await websocket.recv()
        request = json.loads(message)

        if request.get("type") == "get_audio_format":
            print("Server: Received audio format request from client.")
            
            # --- Handshake Step 2: Define and send the audio format ---
            # For this example, we'll use the format from the LineInAudioSource
            print("Server: Please select an audio input device for the server:")
            device = select_audio_device('input')
            
            # Temporarily create the source to determine its actual audio parameters
            # (This is a good pattern as the source itself might adjust parameters)
            temp_source = LineInAudioSource(sink=lambda chunk: None, device=device['name'] if device else None)
            
            audio_format = {
                "type": "audio_format",
                "sample_rate": temp_source.sample_rate,
                "channels": temp_source.channels,
                "dtype": str(temp_source.dtype) # Send dtype as a string
            }
            await temp_source.stop() # No need to keep it running
            
            await websocket.send(json.dumps(audio_format))
            print(f"Server: Sent audio format to client: {audio_format}")

            # --- Handshake Complete: Start streaming ---
            
            # 1. Create a sink that sends audio over the established websocket
            # We pass the determined format to the sink for its own reference
            ws_sink = WebSocketAudioSink(websocket, 
                                         sample_rate=audio_format['sample_rate'],
                                         channels=audio_format['channels'],
                                         dtype=audio_format['dtype'])
            
            # 2. Create the real LineInAudioSource to capture and send audio
            line_in = LineInAudioSource(
                ws_sink.push_chunk,
                disconnect_callback=lambda: print("Server: Microphone source disconnected."),
                device=device['name'] if device else None,
                # Ensure it uses the exact same parameters we sent
                sample_rate=audio_format['sample_rate'],
                channels=audio_format['channels'],
                dtype=audio_format['dtype']
            )

            # 3. Start both the sink and source
            await ws_sink.start()
            await line_in.start()

            # 4. Wait until the WebSocket connection is closed
            await websocket.wait_closed()
        else:
            print(f"Server: Received invalid handshake message: {request}")


    except Exception as e:
        print(f"Server: An error occurred in the handler: {e}")
    finally:
        print("Server: Client disconnected. Cleaning up resources.")
        if line_in:
            await line_in.stop()
        if ws_sink:
            ws_sink.close()

async def start_server():
    """Starts the WebSocket server."""
    print(f"Starting server on ws://{HOST}:{PORT}...")
    server = await websockets.serve(server_handler, HOST, PORT)
    await server.wait_closed()

# --- Client Implementation ---

async def start_client():
    """Starts the WebSocket client."""
    print(f"Connecting to server at {URI}...")
    try:
        async with websockets.connect(URI) as websocket:
            print("Client: Connection successful.")
            player = None
            ws_source = None
            try:
                # --- Handshake Step 1: Request the audio format from the server ---
                await websocket.send(json.dumps({"type": "get_audio_format"}))
                print("Client: Sent audio format request.")

                # --- Handshake Step 2: Wait for the server's response ---
                response_str = await websocket.recv()
                audio_format = json.loads(response_str)

                if audio_format.get("type") != "audio_format":
                    print(f"Client: Received invalid handshake response: {audio_format}")
                    return
                
                print(f"Client: Received audio format from server: {audio_format}")
                source_rate = audio_format['sample_rate']
                source_dtype = audio_format['dtype']

                # --- Handshake Complete: Configure components and start streaming ---
                
                # 1. Create a sink that plays audio to the speakers
                print("Client: Please select an audio output device for the client:")
                device = select_audio_device('output')
                player = AudioPlayerSink(
                    # Use the player's native sample rate for best performance
                    sample_rate=int(device['default_samplerate']),
                    device=device['name'] if device else None
                )
                
                # 2. Create a source that receives audio from the websocket
                ws_source = WebSocketAudioSource(
                    sink=player.push_chunk,
                    websocket=websocket,
                    disconnect_callback=lambda: print("Client: Disconnected from server."),
                    # We now know the exact format of the incoming audio
                    sample_rate=source_rate,
                    dtype=source_dtype
                )

                # 3. Use the convert_output utility to bridge the formats
                #    The source will now automatically convert the server's audio
                #    format to match the speaker's required format.
                ws_source.convert_output(
                    target_sample_rate=player._sample_rate,
                    target_dtype=player._dtype
                )

                # 4. Start the player and the source's receiver task
                await player.start()
                await ws_source.start()

                # 5. Wait until the WebSocket connection is closed
                await websocket.wait_closed()

            except Exception as e:
                print(f"Client: An error occurred: {e}")
            finally:
                print("Client: Connection closed. Cleaning up resources.")
                if ws_source:
                    await ws_source.stop()
                if player:
                    player.close()

    except websockets.exceptions.ConnectionClosedError:
        print("Client: Connection to server failed or was closed.")
    except ConnectionRefusedError:
        print("Client: Connection refused. Is the server running?")

# --- Main Execution ---

async def main():
    """Main entry point to run the client or server."""
    parser = argparse.ArgumentParser(description="WebSocket Audio Streaming Example")
    parser.add_argument('mode', choices=['server', 'client'], help="Run as 'server' or 'client'")
    args = parser.parse_args()

    task = None
    if args.mode == 'server':
        task = asyncio.create_task(start_server())
    elif args.mode == 'client':
        task = asyncio.create_task(start_client())

    if task:
        try:
            await task
        except asyncio.CancelledError:
            pass  # Task cancellation is expected on shutdown

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Shutting down gracefully.")
