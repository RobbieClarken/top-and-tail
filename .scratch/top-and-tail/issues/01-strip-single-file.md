# 01 — Strip a single file to `<name>.stripped.mp3`

**What to build:** The tracer bullet. Running `top-and-tail` against one MP3 source produces a stripped file beside it, named after the source with the extension replaced by `.stripped.mp3`. Leading and trailing silence are gone, internal silence survives untouched, ID3 tags are carried across, and the retained audio is bit-identical to the corresponding region of the source. Settings are the agreed defaults, hardcoded for now: silence threshold −50 dBFS, minimum silence run 0.1 s, padding 50 ms. One source only; no other flags yet.

This ticket also establishes the project's shape — the single executable file with its `uv` script shebang, the committed fixtures, and the pytest suite with both agreed seams present from the start.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] A single executable file named `top-and-tail`, no extension, runnable directly via a `uv run --script` shebang on Python 3.13, with no third-party runtime dependencies
- [ ] ffmpeg decodes the source to raw PCM for in-process analysis; `silencedetect` and its stderr log are not used
- [ ] Silence is a stretch below the silence threshold lasting at least the minimum silence run; briefer quiet is not silence
- [ ] Only the first and last silence are candidates for stripping — everything between is internal silence and is left alone
- [ ] Stripping copies frames via ffmpeg stream copy; the source is never re-encoded
- [ ] ID3 tags are carried from source to destination
- [ ] The boundary arithmetic is a pure function from PCM samples plus the three settings to a pair of boundaries, testable without any file
- [ ] Unit tests over that function cover: quiet shorter than the minimum silence run, quiet exactly at that boundary, an entirely silent buffer, a buffer with no silence, internal silence preserved while both ends strip, padding clamped at the buffer edges, and samples at, just above, and just below the threshold
- [ ] The three examples are committed as test fixtures
- [ ] End-to-end tests invoke the tool as a subprocess against real ffmpeg — never a mock — and assert each fixture reaches its expected duration within frame-quantisation tolerance
- [ ] An end-to-end test decodes both source and destination and asserts the retained region is bit-identical, catching any accidental re-encode
- [ ] An end-to-end test asserts `pretérito` keeps its internal silence, has its leading silence stripped, and is handled correctly despite its non-ASCII filename
- [ ] An end-to-end test asserts ID3 tags survive; `mutagen` may be used as an independent oracle in tests but never in the tool
