# KitchenSink Audio Library

[**Read the Docs**](https://thebestjohn.github.io/KitchenSink/index.html)

---
## Disclaimer

This is a personal project provided as-is for educational and experimental purposes. It makes no claims of suitability for any particular use case and is not guaranteed to work in every environment. While it aims to be a useful tool, it should not be considered a production-ready, professionally supported library.

A modular Python library for building simple audio processing pipelines. `KitchenSink` provides a set of plug-and-play components to easily capture, process, send, receive, and play audio.

## Core Concepts

The library is built around a simple and flexible pipeline model.

### 1. Sources: Where Audio Begins

A **Source** is where audio data originates.
- `LineInAudioSource`: Captures audio from a microphone.
- `TCPServerAudioSource` / `WebSocketServerAudioSource`: Receives audio from a network connection.

### 2. Sinks & Consumers: Where Audio Goes

A **Sink** is a destination for audio. This can be a traditional sink that outputs audio, or any other function that "consumes" the audio data.
- `AudioPlayerSink`: Plays audio to your speakers.
- `TCPClientAudioSink` / `WebSocketClientAudioSink`: Sends audio over a network connection.
- `Your Own Function`: A function that performs analysis, like speech-to-text.

### 3. Building Pipelines

You connect components by passing a callable (like a sink's `push_chunk` method or your own function) to a source's constructor. This allows you to create chains:

- **Simple Pipeline**: `[Mic Source] -> [Network Sink]`
- **Middleware**: Chain components to process audio mid-stream. `[Mic Source] -> [Volume Monitor] -> [Network Sink]`
- **Consumers**: End a pipeline with a function instead of a sink. `[Network Source] -> [Speech-to-Text Function]`

### 4. Blocksize: Managing Audio Chunks
The `blocksize` parameter, available in most sources and sinks, defines the number of audio frames per chunk. This is a key parameter for controlling latency and performance.

- **In Sources**: It determines how frequently the source will generate and push audio chunks to the sink.
- **In Sinks**: It serves as a hint to the source about the preferred chunk size for optimal processing (e.g., matching the buffer size of the audio output device).

A smaller `blocksize` reduces latency but increases the overhead of function calls and network packets. A larger `blocksize` is more efficient but introduces more delay. The ideal value depends on the application's requirements.

## Installation

Install the library using `pip`:

```bash
pip install .
```

### Windows Optional Dependencies

For improved, lower-latency audio playback on Windows, you can install the optional `winsdk` dependencies:

```bash
pip install .[win_bleeding_edge]
```

## Components

### Sources
-   **`LineInAudioSource`**: Captures audio from a local microphone/line-in. `blocksize` controls the chunk size.
-   **`TCPServerAudioSource`**: Listens for a single raw TCP client connection and receives audio data. `blocksize` defines the expected size of incoming data chunks.
-   **`RawWebSocketServerAudioSource`**: Listens for a single WebSocket client and receives raw binary audio data. It processes whatever chunk size it receives but can be initialized with a `blocksize` for consistency.
-   **`TypedWebSocketServerAudioSource`**: Listens for a WebSocket client and handles structured JSON messages. It also processes any received chunk size.

### Sinks
-   **`AudioPlayerSink`**: Plays audio to local speakers. `blocksize` can hint to the source about the preferred chunk size for the audio device.
-   **`TCPClientAudioSink`**: Connects to a raw TCP server and sends audio data.
-   **`RawWebSocketClientAudioSink`**: Connects to a WebSocket server and sends raw binary audio data.
-   **`TypedWebSocketClientAudioSink`**: Connects to a WebSocket server and sends structured JSON messages.

## Example Usage

The `examples/` directory contains scripts demonstrating how to use the library. All examples feature interactive device selection where applicable.

### Raw TCP
-   **`network_to_speaker.py`**: The server. Listens for a TCP connection and plays received audio.
-   **`mic_to_network.py`**: The client. Captures audio from a microphone and sends it to the TCP server.

### Raw WebSocket
-   **`raw_websocket_loopback.py`**: A self-contained example that demonstrates a high-performance, audio-only loopback from microphone to speaker using raw WebSockets.

### Typed WebSocket (for Audio and other data)
-   **`websocket_loopback.py`**: A self-contained example demonstrating a loopback that can handle both audio streams and other message types (like text) using a structured JSON protocol.
