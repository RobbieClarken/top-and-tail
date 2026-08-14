# Silence Stripper

A command line tool that removes silence from the start and end of MP3 files, without touching the audio in between. It exists because text-to-speech vocabulary audio arrives heavily padded — in practice the majority of each file is silence.

## Language

**Utterance**:
The audible content of a source file — a single spoken vocabulary item. Everything the tool preserves.
_Avoid_: Speech, clip, sample

**Silence**:
A stretch of audio that stays below the silence threshold for at least the minimum silence run. Quiet that is too brief to clear the run length is not silence.
_Avoid_: Quiet, blank, dead air

**Leading silence**:
Silence before the utterance begins. Stripped.

**Trailing silence**:
Silence after the utterance ends. Stripped.

**Internal silence**:
Silence between two audible parts of the same utterance — the stop consonant in *pretérito*, for example. Never stripped; removing it would mangle the word.
_Avoid_: Gap, pause

**Silence threshold**:
The amplitude below which audio counts as silent.

**Minimum silence run**:
How long audio must stay below the silence threshold before it counts as silence rather than a brief dip.

**Padding**:
A margin of silence deliberately retained at each end of the utterance, so that a word's natural onset and decay are not clipped.
_Avoid_: Buffer, lead-in, tail

**Strip**:
To produce a file containing the utterance plus padding, with leading and trailing silence removed.
_Avoid_: Trim, cut, truncate, clean

**Top and tail**:
The audio-engineering term for stripping both ends of a clip while leaving its middle intact — the tool's entire contract, and its name.

**Frame**:
The atomic unit of an MP3 file, roughly 26 ms of audio. Stripping happens on frame boundaries, so cut points quantise to that granularity and the retained audio survives byte-for-byte.

**Unchanged**:
The outcome when a source file has no leading or trailing silence to strip — including a file that is silent throughout. The destination is still written, as an exact copy of the source. The one exception is an in-place strip, where an unchanged source is left completely untouched rather than rewritten with identical bytes.

**Source**:
The input file being read. Never modified except by an explicit in-place strip.
_Avoid_: Original, input file

**Destination**:
The file the stripped result is written to. Always written, even when the outcome is unchanged.
_Avoid_: Output file, target
