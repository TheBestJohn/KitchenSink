# KitchenSink Audio Library

## Disclaimer

This is a personal project provided as-is for educational and experimental purposes. It makes no claims of suitability for any particular use case and is not guaranteed to work in every environment. While it aims to be a useful tool, it should not be considered a production-ready, professionally supported library.

A modular Python library for building simple audio processing pipelines. `KitchenSink` provides a set of plug-and-play "sources" and "sinks" to easily capture, send, receive, and play audio.

## Core Concepts

-   **Sources**: Originate audio data. Examples include capturing from a microphone (`LineInAudioSource`) or receiving data from a network stream (`TCPServerAudioSource`).
-   **Sinks**: Terminate audio data. Examples include playing audio through speakers (`AudioPlayerSink`) or sending data to a network stream (`TCPClientAudioSink`).

All sources and sinks are built on a common base class, making them easy to extend and interchange.

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
-   **`LineInAudioSource`**: Captures audio from a local microphone/line-in.
-   **`TCPServerAudioSource`**: Listens for a single raw TCP client connection and receives audio data.
-   **`RawWebSocketServerAudioSource`**: Listens for a single WebSocket client and receives raw binary audio data.
-   **`TypedWebSocketServerAudioSource`**: Listens for a WebSocket client and handles structured JSON messages for audio, text, or custom events.

### Sinks
-   **`AudioPlayerSink`**: Plays audio to local speakers. Uses `WinSDK` for low-latency on Windows if available, otherwise falls back to `sounddevice`.
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
