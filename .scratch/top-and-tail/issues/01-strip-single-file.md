# 01 — Strip a single file to `<name>.stripped.mp3`

**What to build:** The tracer bullet. Running `top-and-tail` against one MP3 source produces a stripped file beside it, named after the source with the extension replaced by `.stripped.mp3`. Leading and trailing silence are gone, internal silence survives untouched, ID3 tags are carried across, and the retained audio is bit-identical to the corresponding region of the source. Settings are the agreed defaults, hardcoded for now: silence threshold −50 dBFS, minimum silence run 0.1 s, padding 50 ms. One source only; no other flags yet.

This ticket also establishes the project's shape — the single executable file with its `uv` script shebang, the committed fixtures, and the pytest suite with both agreed seams present from the start.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [x] A single executable file named `top-and-tail`, no extension, runnable directly via a `uv run --script` shebang on Python 3.13, with no third-party runtime dependencies
- [x] ffmpeg decodes the source to raw PCM for in-process analysis; `silencedetect` and its stderr log are not used
- [x] Silence is a stretch below the silence threshold lasting at least the minimum silence run; briefer quiet is not silence
- [x] Only the first and last silence are candidates for stripping — everything between is internal silence and is left alone
- [x] Stripping copies frames via ffmpeg stream copy; the source is never re-encoded
- [x] ID3 tags are carried from source to destination
- [x] The boundary arithmetic is a pure function from PCM samples plus the three settings to a pair of boundaries, testable without any file
- [x] Unit tests over that function cover: quiet shorter than the minimum silence run, quiet exactly at that boundary, an entirely silent buffer, a buffer with no silence, internal silence preserved while both ends strip, padding clamped at the buffer edges, and samples at, just above, and just below the threshold
- [x] The three examples are committed as test fixtures
- [x] End-to-end tests invoke the tool as a subprocess against real ffmpeg — never a mock — and assert each fixture reaches its expected duration within frame-quantisation tolerance
- [x] An end-to-end test decodes both source and destination and asserts the retained region is bit-identical, catching any accidental re-encode
- [ ] An end-to-end test asserts `pretérito` keeps its internal silence, has its leading silence stripped, and is handled correctly despite its non-ASCII filename
- [x] An end-to-end test asserts ID3 tags survive; `mutagen` may be used as an independent oracle in tests but never in the tool

## Comments

**Implemented in `912005c`, review fixes to follow.** 12 of 13 criteria met; 23 tests pass.

**The one unchecked criterion cannot be met as written.** No fixture has strippable leading silence at the agreed defaults. `pretérito` does carry ~61 ms of leading quiet, but that is under the 0.1 s minimum silence run, so by our own definition it is not silence and must not be stripped. `hablar` opens with 47 ms, likewise under the run. The criterion was written from a `silencedetect` pass using `d=0.05`, which is half our minimum run.

Covered instead by three tests, which together exceed what the original criterion asked for:

- `test_internal_silence_survives_stripping` — `pretérito`'s internal silence, asserted directly on decoded samples either side of the stop consonant.
- `test_a_non_ascii_source_name_is_handled` — the accented filename.
- `test_leading_quiet_below_the_minimum_run_is_kept` — the inverse property: quiet under the minimum run must survive.
- `test_leading_silence_is_stripped` — leading stripping proper, against a source built by prepending a second of silence to `hablar`, since no shipped fixture can exercise it.

**Also found:** ffmpeg's mp3 muxer always rewrites the `encoder` (`TSSE`) tag, so the sources' only shipped tag is replaced rather than carried. Neither `-bitexact` (drops every tag) nor an explicit `-metadata` override prevents it. User-set tags such as `TIT2`/`TPE1` do survive. This contradicts the parent spec's "carried across unmodified; nothing is added, removed or rewritten" and needs a decision — see `test_the_muxer_rewrites_the_encoder_tag`, which pins the current behaviour.

**Deferred:** ADR-0001 requires the `min-silence > padding + 26 ms` invariant to be "validated at startup". Ticket 05 owns the flags that make it violable; no validation exists yet.

**Bug found later: a tail artifact defeated trailing-silence detection.**

`find_bounds` scanned back from the very last sample and stopped at the first thing above the threshold, so trailing silence was only ever found if it reached the end of the buffer. The `él` fixture ends with eleven stray samples in its final 3.1 ms, peaking at −44.7 dBFS — 0.017% of the file — and that was enough to hide 1.15 s of silence and report the whole thing as unchanged. `hablar` only escaped by luck: its final samples measure 1 to 3, far below the limit.

Fixed by judging sound the same way as quiet: a burst shorter than the minimum silence run, cut off from the utterance by silence, is an artifact rather than speech. The rule is symmetric, so a click at the start cannot hide leading silence either. No new setting — the existing minimum silence run is the yardstick.

`find_bounds` now works from the maximal runs of quiet rather than scanning inward from each edge, which made the rule expressible without a second pass. All twelve original unit cases pass unchanged. New terms in `CONTEXT.md`: **Artifact**.
