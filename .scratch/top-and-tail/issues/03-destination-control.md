# 03 — Destination control: `--inplace` and `-o`

**What to build:** Control over where the stripped result lands. `--inplace` overwrites the source, but only ever by writing a temporary file in the same directory and atomically renaming it over the source, so an interrupted run can never leave a truncated file where a good one was. `-o`/`--output` names a single destination file.

Two combinations are contradictory and must be rejected outright: `-o` alongside more than one source, and `-o` alongside `--inplace`. A destination that resolves to the same file as its source is not an error — it is treated as an in-place strip and takes the atomic path, so the file is never truncated while being read.

The in-place flag has no short form. `-i` means *input* in ffmpeg and most audio tooling, and typing it here by muscle memory would silently overwrite a source.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] `--inplace` replaces the source with the stripped result
- [ ] In-place writes go to a temporary file in the same directory and are atomically renamed; an interrupted run leaves the source intact
- [ ] There is no `-i` short form for `--inplace`
- [ ] `-o`/`--output` writes the result to the named destination
- [ ] An existing file at the destination is overwritten without prompting
- [ ] `-o` with more than one source is rejected with a clear message and a non-zero exit
- [ ] `-o` with `--inplace` is rejected with a clear message and a non-zero exit
- [ ] A destination resolving to its own source is handled as an in-place strip, with no truncation
- [ ] End-to-end tests cover each destination mode, both rejected combinations, and the source-equals-destination case
