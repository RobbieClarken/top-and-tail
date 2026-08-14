# 02 — Batch several sources, with reporting and exit codes

**What to build:** Accepting more than one source in a single invocation, and telling the user what happened. Each source gets a line on stdout naming it and giving the duration before and after with the percentage saved. A summary line closes the batch. A run in which every source succeeded exits zero.

Sources are explicit file paths only. Directories are not accepted and nothing is ever walked recursively — shell globbing covers the batch case.

**Blocked by:** 01

**Status:** ready-for-agent

- [x] Several explicit file paths can be passed in one invocation and each is stripped
- [x] One line per source on stdout, giving the source name, duration before, duration after, and percentage saved
- [x] A summary line closes a batch
- [x] A directory passed as a source is rejected with a clear message rather than walked
- [x] A run where every source succeeded exits zero
- [x] End-to-end tests cover a multi-source run, the shape of the per-file and summary output, and the exit code

## Comments

**Implemented.** All six criteria met; 29 tests pass, mypy clean.

**Report durations come from `ffprobe`, not from decoding.** The two disagree after a cut: `hablar` stripped decodes to 0.680s but every player and `ffprobe` reports 0.692s, because the gapless-playback info in the Xing header changes when frames are removed. Measuring the "before" one way and the "after" the other made a re-run of an already-stripped file report that it had *grown*. Both ends now come from `ffprobe`, pinned by `test_a_rerun_never_reports_the_file_growing`, which was verified to fail under the mixed measurement. This introduces `ffprobe` as a second external binary — see the note appended to ticket 06.

**A single source gets no summary line.** "A summary line closes a batch" reads as plural; restating the one line above it is noise. Pinned by `test_a_single_source_gets_no_summary`.

**Directories exit 2**, matching argparse's convention for usage errors, and are rejected before any source is processed rather than part-way through. Ticket 06 owns the general non-zero-on-failure behaviour and may want a different code for source failures.
