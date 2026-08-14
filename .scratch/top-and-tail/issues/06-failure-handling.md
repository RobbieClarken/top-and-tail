# 06 — Failure handling

**What to build:** Every failure named clearly, and a batch that survives one. An invalid or corrupt MP3 is reported as an error rather than passing through silently — a failed download must not go unnoticed in a pipeline. An unwritable destination is reported with the source left intact, so a permissions problem never costs audio. A missing ffmpeg names the missing dependency rather than surfacing as a confusing crash.

One bad source does not stop the rest of the batch: the remaining sources are still stripped, each failure is reported, and the process exits non-zero at the end so a script can detect trouble without parsing output.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] An invalid or corrupt MP3 is reported as a named error
- [ ] An unwritable destination is reported as a named error and the source is left intact
- [ ] A missing ffmpeg is reported as a named error identifying the missing dependency
- [ ] A source path that does not exist is reported as a named error
- [ ] A failing source does not prevent the remaining sources in the batch being processed
- [ ] The process exits non-zero if any source failed, and zero when all succeeded — including when all were `unchanged`
- [ ] A failure under `--inplace` leaves the source intact, with no temporary file left behind
- [ ] End-to-end tests cover each failure mode and the mixed batch of good and bad sources

## Comments

**Scope note from ticket 02.** Reporting needs container durations, which come from `ffprobe`, so the tool now shells out to two binaries rather than one. The criterion "A missing ffmpeg is reported as a named error" should be read as covering **ffprobe too** — they ship together, but a minimal build can omit ffprobe, and its absence currently surfaces as an unhandled `FileNotFoundError`.

Ticket 02 also established the shape for a clean rejection: a message on stderr naming the offending path, and no stack trace. `test_a_directory_source_is_rejected_rather_than_walked` asserts `"Traceback" not in stderr` — worth copying for the failure modes here, since an unhandled exception can otherwise pass a naive "non-zero exit and the right word in stderr" assertion.
