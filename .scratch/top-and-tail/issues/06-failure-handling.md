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
- [x] A failure under `--in-place` leaves the source intact, with no temporary file left behind
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

**Follow-up fixes, from checking edge cases by hand.**

The two-axis review could not be run — the sub-agents failed with repeated server-side 529s — so the adversarial pass below was done in one context by the implementer, which is weaker. **Worth re-running `/code-review` over this ticket when the API recovers.**

*A source whose relative name begins with a dash was reported as unreadable.* `ffprobe` takes its input as a positional argument, so `-dash.mp3` was parsed as an option and failed with "Missing argument for option 'dash.mp3'" — a valid MP3 reported as `not a readable MP3`. `Path("./-dash.mp3")` normalises away the `./`, so even writing the prefix did not help. Every subprocess argument is now rendered absolute, which can never begin with a dash. Pinned by a test verified to fail when the fix is reverted.

*The dependency message named the wrong tool.* With only `ffprobe` missing it still read "needs ffmpeg installed". It now names both and says they ship together, and the test is parametrised over ffmpeg-absent and ffprobe-absent-alone.

Checked clean with no stack trace, exit 1: empty `.mp3`, truncated `.mp3`, dangling symlink, symlink loop, unreadable file, FIFO, a directory as `-o`, a missing parent directory for `-o`, the same source twice, a relative path containing `..`, and a leading-dash name.

**Known rough edge, not fixed:** a source with no read permission reports `not a readable MP3` rather than a permissions problem. Accurate in that ffmpeg cannot read it, but it points at the wrong cause. Distinguishing the two means stat-ing before decoding, which would be one more thing to keep in step with reality.

**Two-axis review, second attempt.** The first attempt failed with repeated server-side 529s; running the axes one at a time rather than in parallel worked. Both axes found real problems, and every one of them was in the *tests* rather than the behaviour.

*The dependency test could not fail.* It asserted the missing tool's name appeared in stderr, but the message ends with "needs ffmpeg and ffprobe, which ship together" — so both names are always present and the assertion held even when the prefix named the wrong tool. It would have passed against the code from before that fix. Now asserted on the leading clause.

*The temporary-cleanup test never reached the cleanup path.* It used a corrupt source, which fails in `probe_duration` before `mkstemp` is ever called, so `scratch.unlink` was never executed. Replaced with a write to an existing directory, which gets all the way to the rename before failing. The behaviour was correct all along; the test was hollow.

*The unwritable-destination test never checked the error was named*, and no test asserted a failing source survives byte-for-byte. Both added.

*One escape path remained*: `existing.stat()` sat outside the `try` in `place`, so an `OSError` there would have surfaced as a traceback. Narrow in practice, since `Path.exists()` swallows the permission cases, but now inside it. The handling is also restructured — an inner `except OSError` translating, wrapped in an outer `except BaseException` guaranteeing cleanup survives even a `KeyboardInterrupt` — rather than dispatching on `isinstance` inside a single broad clause.

*Messages named the wrong cause* for three kinds of source. A single `is_file()` gate reported `no such file` for a FIFO and for a dangling symlink, which plainly exist, and `not a readable MP3` for a file with no read permission. `check_source` now distinguishes broken symlink, not a regular file, and not readable. The earlier note here called this not worth fixing on maintenance grounds; that was wrong, since `main` already stats the source and `os.access` is one line.

*The failure summary contradicted the file's own rule.* `1 of 1 sources failed` restates the line above it, which the code elsewhere calls noise. Now printed only for a batch.

Also from review: the batch loop is extracted as `strip_all`, leaving `main` as argument parsing, guards and the exit-code map.
