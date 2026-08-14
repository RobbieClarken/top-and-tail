# 02 — Batch several sources, with reporting and exit codes

**What to build:** Accepting more than one source in a single invocation, and telling the user what happened. Each source gets a line on stdout naming it and giving the duration before and after with the percentage saved. A summary line closes the batch. A run in which every source succeeded exits zero.

Sources are explicit file paths only. Directories are not accepted and nothing is ever walked recursively — shell globbing covers the batch case.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Several explicit file paths can be passed in one invocation and each is stripped
- [ ] One line per source on stdout, giving the source name, duration before, duration after, and percentage saved
- [ ] A summary line closes a batch
- [ ] A directory passed as a source is rejected with a clear message rather than walked
- [ ] A run where every source succeeded exits zero
- [ ] End-to-end tests cover a multi-source run, the shape of the per-file and summary output, and the exit code
