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
