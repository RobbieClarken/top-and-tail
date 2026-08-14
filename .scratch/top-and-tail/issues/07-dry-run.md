# 07 — `--dry-run`

**What to build:** A way to preview a run before committing to it, which matters most before a destructive `--inplace` pass. `--dry-run` performs the full analysis and produces exactly the report a real run would, but writes nothing to disk — no destinations, no temporary files, no in-place replacements.

**Blocked by:** 02, 03

**Status:** ready-for-agent

- [ ] `--dry-run` reports per-source durations before and after, and the percentage saved, as a real run would
- [ ] `--dry-run` writes nothing: no destination file is created, no source is modified, no temporary file is left behind
- [ ] `--dry-run` works alongside `--inplace` and `-o`, reporting what each would have done
- [ ] `unchanged` outcomes are reported under `--dry-run` as they would be in a real run
- [ ] The output makes clear that nothing was written
- [ ] Exit codes match what the equivalent real run would produce
- [ ] End-to-end tests assert the filesystem is untouched after a `--dry-run` in each destination mode
