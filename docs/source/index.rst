
.. KitchenSink Audio documentation master file.

###################################
KitchenSink Audio Documentation
###################################

Welcome to the official documentation for KitchenSink Audio. This library provides
a simple, modular framework for building audio processing pipelines.

Core Concepts
-------------

The library is built around two fundamental concepts: **Sources** and **Sinks**.

*   A **Source** is where audio comes from. This could be a local microphone
    (``LineInAudioSource``), a network connection (like ``TCPServerAudioSource``),
    or any other origin of audio data.
*   A **Sink** is where audio goes to. This could be your speakers
    (``AudioPlayerSink``), a network connection (like ``TCPClientAudioSink``),
    or a file on disk.

You connect them by passing a sink's ``push_chunk`` method as the ``sink``
argument when creating a source. The source then calls this method to send
its audio data to the sink, creating a pipeline.

Middleware and Pipelines
------------------------

To process or analyze audio between a source and a final sink, you can create
"middleware" components. A middleware component is simply a class that acts as
both a sink and a source.

1.  It accepts a ``sink`` in its constructor, just like a real source.
2.  It has a ``push_chunk`` method, just like a real sink.

When its ``push_chunk`` method is called, it can perform an action on the audio
data (e.g., measure volume, apply an effect, log data) and then pass the chunk
along to the *next* sink in the chain.

This allows you to build complex pipelines:

.. code-block:: text

   [Mic Source] -> [Volume Monitor Middleware] -> [Network Sink]


Consuming Chunks
----------------

The callable you provide as a ``sink`` does not have to be an actual ``BaseAudioSink``
object. It can be any function or method that can process a chunk of audio data.

This is useful for when the audio stream is not meant for another destination,
but is instead being consumed for analysis. For example, you could have a
WebSocket source feed audio chunks directly to a speech-to-text engine:

.. code-block:: text

   def speech_to_text_engine(audio_chunk):
       # Process the audio, get transcription...
       transcription = my_stt_library.process(audio_chunk)
       # ...then do something with the text.
       if transcription:
           print(f"Heard: {transcription}")

   # The STT function is the "sink" for the audio source.
   ws_source = TypedWebSocketServerAudioSource(sink=speech_to_text_engine)


This pattern allows you to use the sources in this library as a generic way to
receive audio for any purpose.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api_reference

.. mdinclude:: ../../README.md


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
