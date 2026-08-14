# Lossless frame-boundary stripping

Source files are lossy TTS output with no headroom for a second generation of encoding loss, so we strip by copying MP3 frames rather than by decoding and re-encoding. Measured on `examples/hablar-…mp3`: cutting with `ffmpeg -c copy` left the retained region bit-identical (`cmp` over 52,920 bytes of decoded PCM reported no difference) and rewrote the Xing/Info frame count correctly (75 → 27 frames), so no header repair is needed on our side.

## Consequences

Cut points quantise to the MP3 frame size of roughly 26 ms, and ffmpeg rounds toward keeping audio — a cut requested at 0.667 s landed at 0.692 s. This is invisible next to the padding we deliberately retain, but it interacts with idempotency:

**`min-silence` must be greater than `padding + 26 ms`, and this is validated at startup.** After a strip, the quiet remaining at each end is the padding plus up to a frame of rounding. If that residue is long enough to count as silence on a later run, every re-run eats another slice of the utterance. At the defaults (padding 50 ms, min-silence 100 ms) the residue measures 63 ms, comfortably under the bar — verified by re-running detection on a stripped file. Raising padding above ~74 ms without raising `min-silence` would break idempotency, which is why the relationship is asserted rather than left to documentation.

## Considered options

**Re-encoding** would give sample-exact cut points instead of frame-quantised ones. Rejected: the precision is worthless next to 50 ms of intentional padding, and it costs a lossy generation on every run of a tool designed to be run repeatedly.

**Hand-rolling the frame parsing and Xing rewrite** in Python, using ffmpeg only to decode PCM for analysis. Rejected once `-c copy` was measured to be bit-exact and to fix the Xing header itself. `mutagen` is the library to reach for if that ever disappoints.

**pydub**, which ships `strip_silence()` and `detect_leading_silence()`. Rejected twice over: it re-encodes on export, defeating the whole decision, and version 0.25.1 (last released 2021) does not import on Python 3.13 at all, since it depends on the `audioop` module removed by PEP 594.
