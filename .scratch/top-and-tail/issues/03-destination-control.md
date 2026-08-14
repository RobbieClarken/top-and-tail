# 03 — Destination control: `--inplace` and `-o`

**What to build:** Control over where the stripped result lands. `--inplace` overwrites the source, but only ever by writing a temporary file in the same directory and atomically renaming it over the source, so an interrupted run can never leave a truncated file where a good one was. `-o`/`--output` names a single destination file.

Two combinations are contradictory and must be rejected outright: `-o` alongside more than one source, and `-o` alongside `--inplace`. A destination that resolves to the same file as its source is not an error — it is treated as an in-place strip and takes the atomic path, so the file is never truncated while being read.

The in-place flag has no short form. `-i` means *input* in ffmpeg and most audio tooling, and typing it here by muscle memory would silently overwrite a source.

**Blocked by:** 01

**Status:** ready-for-agent

- [x] `--inplace` replaces the source with the stripped result
- [x] In-place writes go to a temporary file in the same directory and are atomically renamed; an interrupted run leaves the source intact
- [x] There is no `-i` short form for `--inplace`
- [x] `-o`/`--output` writes the result to the named destination
- [x] An existing file at the destination is overwritten without prompting
- [x] `-o` with more than one source is rejected with a clear message and a non-zero exit
- [x] `-o` with `--inplace` is rejected with a clear message and a non-zero exit
- [x] A destination resolving to its own source is handled as an in-place strip, with no truncation
- [x] End-to-end tests cover each destination mode, both rejected combinations, and the source-equals-destination case

## Comments

**Implemented.** All nine criteria met; 38 tests pass, mypy clean.

**Every write is atomic, not just in-place ones.** The result goes to a temporary file in the destination's own directory — so the rename stays on one filesystem — and is then renamed over the destination. Doing this for all destinations is one code path rather than two, and it is what makes a destination pointing at its own source safe for free.

That safety is not theoretical. With the atomic write removed, `test_a_destination_that_is_its_own_source_strips_in_place` fails outright: ffmpeg truncates the file while it is still reading it. The atomic path is load-bearing, not belt-and-braces.

**Evidence for temp-and-rename**, rather than just trusting the code: `test_inplace_writes_via_a_temporary_and_renames` asserts the file's inode changes across a run. A direct write would keep it. Verified to fail when the atomic write is removed.

**The two rejected combinations exit 2 by different routes.** `-o` with `--inplace` is an argparse mutually-exclusive group, which produces the usage message for free. `-o` with several sources is a manual check, because argparse cannot express "this option requires exactly one positional". Both exit 2, consistent with the directory rejection from ticket 02.

**Deferred to ticket 06:** a failed write currently leaves the source intact — asserted by `test_a_failed_inplace_write_leaves_the_source_intact`, which makes the directory read-only — but reports it as an unhandled traceback rather than a named error.
