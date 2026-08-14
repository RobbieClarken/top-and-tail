# 06 — Failure handling

**What to build:** Every failure named clearly, and a batch that survives one. An invalid or corrupt MP3 is reported as an error rather than passing through silently — a failed download must not go unnoticed in a pipeline. An unwritable destination is reported with the source left intact, so a permissions problem never costs audio. A missing ffmpeg names the missing dependency rather than surfacing as a confusing crash.

One bad source does not stop the rest of the batch: the remaining sources are still stripped, each failure is reported, and the process exits non-zero at the end so a script can detect trouble without parsing output.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [x] An invalid or corrupt MP3 is reported as a named error
- [x] An unwritable destination is reported as a named error and the source is left intact
- [x] A missing ffmpeg is reported as a named error identifying the missing dependency
- [x] A source path that does not exist is reported as a named error
- [x] A failing source does not prevent the remaining sources in the batch being processed
- [x] The process exits non-zero if any source failed, and zero when all succeeded — including when all were `unchanged`
- [x] A failure under `--inplace` leaves the source intact, with no temporary file left behind
- [x] End-to-end tests cover each failure mode and the mixed batch of good and bad sources

## Comments

**Scope note from ticket 02.** Reporting needs container durations, which come from `ffprobe`, so the tool now shells out to two binaries rather than one. The criterion "A missing ffmpeg is reported as a named error" should be read as covering **ffprobe too** — they ship together, but a minimal build can omit ffprobe, and its absence currently surfaces as an unhandled `FileNotFoundError`.

Ticket 02 also established the shape for a clean rejection: a message on stderr naming the offending path, and no stack trace. `test_a_directory_source_is_rejected_rather_than_walked` asserts `"Traceback" not in stderr` — worth copying for the failure modes here, since an unhandled exception can otherwise pass a naive "non-zero exit and the right word in stderr" assertion.

**Implemented.** All eight criteria met; 65 tests pass, mypy clean.

**One exception type, translated at the boundary.** `Failure` carries a message meant for the user. `decode`, `probe_duration`, `copy_frames` and `place` each translate the low-level error they can raise — `CalledProcessError`, `ValueError`, `OSError` — into a `Failure` that says what went wrong in that specific operation. `main` catches only `Failure`, so anything else still raises loudly rather than being swallowed as a routine problem.

**Dependencies are checked once at startup**, not per source, since without them nothing can succeed and repeating the message for every source would be noise. Exit 2, consistent with the other environment and usage errors. Covered by a test that runs the tool with a `PATH` holding only `uv`, so the shebang still resolves while ffmpeg does not.

**Exit codes:** 2 for usage and environment problems, caught before any work starts; 1 when some sources failed but the batch ran; 0 when everything succeeded, including `unchanged` sources.

**The scope note from ticket 02 is discharged** — `ffprobe` is checked alongside `ffmpeg`, and both are named in the error.

**Also translated `copy_frames` failures**, which the criteria do not mention. It shells out to ffmpeg and could raise `CalledProcessError` from any write problem, which would have been the one remaining path to a traceback.

Every failure test asserts `"Traceback" not in stderr`, following the shape ticket 02 established — without it a test can pass against an unhandled exception whose text happens to contain the right words.
