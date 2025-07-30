
API Reference
=============

This page provides an auto-generated summary of the KitchenSink Audio library's public API.

Sources
-------

Sources are responsible for acquiring audio data.

.. autoclass:: kitchensink.sources.base_source.BaseAudioSource
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sources.line_in_source.LineInAudioSource
   :members: list_input_devices
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sources.network_audio_source.TCPServerAudioSource
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sources.raw_websocket_audio_source.RawWebSocketServerAudioSource
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sources.typed_websocket_audio_source.TypedWebSocketServerAudioSource
   :members:
   :undoc-members:
   :show-inheritance:


Sinks
-----

Sinks are the destination for audio data.

.. autoclass:: kitchensink.sinks.base_sink.BaseAudioSink
   :members:
   :undoc-members:
   :show-inheritance:

.. automethod:: kitchensink.sinks.audio_player_sink.AudioPlayerSink

.. autoclass:: kitchensink.sinks.network_audio_sink.TCPClientAudioSink
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sinks.raw_websocket_audio_sink.RawWebSocketClientAudioSink
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kitchensink.sinks.typed_websocket_audio_sink.TypedWebSocketClientAudioSink
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

.. automethod:: kitchensink.utils.select_audio_device
