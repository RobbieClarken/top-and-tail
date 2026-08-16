"""Seam 1: the CLI, invoked as a subprocess against real ffmpeg."""

import os
import shutil
import stat
import subprocess
from array import array

import pytest

from conftest import TOOL, copy_fixture

RATE = 44100
PADDING = 0.050
FRAME = 1152 / RATE  # an MP3 frame at this rate, ~26ms

# Where the utterance ends in each fixture, measured independently with
# ffmpeg's silencedetect during design. The tool keeps 50ms of padding beyond
# this and then rounds up to the next 26ms frame boundary.
UTTERANCE_ENDS = {
    "yo-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3": 0.404,
    "hablar-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3": 0.617,
    "pretérito-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3": 0.748,
    "él-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3": 0.291,
}


def run(*args):
    return subprocess.run(
        [str(TOOL), *[str(a) for a in args]],
        capture_output=True,
        text=True,
    )


def _probe(path, entries):
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", entries,
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(probe.stdout.strip().splitlines()[0])


def duration(path):
    return _probe(path, "format=duration")


def audio_length(path):
    """Duration of the audio itself, excluding the stream's start offset.

    These sources begin at 0.025057s and the stream copy carries that offset
    across, so the container duration reads that much longer than the audio.
    """
    return duration(path) - _probe(path, "stream=start_time")


def make_silent_mp3(path, seconds=1.0):
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", f"anullsrc=r={RATE}:cl=mono",
            "-t", str(seconds), "-c:a", "libmp3lame", "-b:a", "128k",
            str(path),
        ],
        check=True,
    )
    return path


def assert_stripped(path, seconds=0.692):
    """The fixture durations after stripping, within frame-rounding slack."""
    assert abs(duration(path) - seconds) < 0.03, duration(path)


def pcm(path):
    """Decode to raw mono samples, independently of the tool."""
    decoded = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-",
        ],
        capture_output=True,
        check=True,
    )
    return decoded.stdout


def test_strips_trailing_silence_to_a_stripped_sibling(hablar):
    result = run(hablar)

    assert result.returncode == 0, result.stderr
    stripped = hablar.with_suffix(".stripped.mp3")
    assert stripped.exists()
    assert duration(stripped) < duration(hablar)


@pytest.mark.parametrize("name", sorted(UTTERANCE_ENDS))
def test_every_fixture_is_stripped_to_the_expected_duration(name, tmp_path):
    source = copy_fixture(name, tmp_path)

    assert run(source).returncode == 0

    kept = audio_length(source.with_suffix(".stripped.mp3"))
    utterance_end = UTTERANCE_ENDS[name]
    # None of the utterance may be lost...
    assert kept >= utterance_end
    # ...and the silence beyond it is gone, bar the padding and the frame the
    # cut rounds up to.
    assert kept <= utterance_end + PADDING + FRAME


def test_retained_audio_is_bit_identical_to_the_source(hablar):
    run(hablar)

    source_pcm = pcm(hablar)
    stripped_pcm = pcm(hablar.with_suffix(".stripped.mp3"))

    # The final frames of a truncated stream decode differently, so compare
    # everything but the last 50ms. Any re-encode would break this outright.
    compared = len(stripped_pcm) - (RATE // 20) * 2
    assert compared > 0
    assert stripped_pcm[:compared] == source_pcm[:compared]


def test_internal_silence_survives_stripping(preterito):
    run(preterito)
    samples = array("h", pcm(preterito.with_suffix(".stripped.mp3")))

    def loudest(start, end):
        return max(abs(s) for s in samples[int(start * RATE):int(end * RATE)])

    # pretérito is quiet between 0.560s and 0.618s, around the stop consonant,
    # and audible either side. All three regions must survive the strip.
    assert loudest(0.570, 0.610) <= 104
    assert loudest(0.300, 0.500) > 104
    assert loudest(0.650, 0.740) > 104


def test_leading_quiet_below_the_minimum_run_is_kept(hablar):
    # hablar opens with 47ms of quiet, which is under the 0.1s minimum silence
    # run, so it is not silence and must not be stripped.
    run(hablar)

    source_pcm = pcm(hablar)
    stripped_pcm = pcm(hablar.with_suffix(".stripped.mp3"))
    opening = (RATE // 20) * 2
    assert stripped_pcm[:opening] == source_pcm[:opening]


def test_a_non_ascii_source_name_is_handled(preterito):
    assert run(preterito).returncode == 0

    stripped = preterito.with_suffix(".stripped.mp3")
    assert stripped.exists()
    assert "pretérito" in stripped.name


def test_leading_silence_is_stripped(hablar, tmp_path):
    # No fixture has strippable leading silence — the most any of them opens
    # with is hablar's 47ms, under the 0.1s minimum run. So build a source that
    # does, by prepending a second of silence.
    padded = tmp_path / "padded.mp3"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", str(hablar),
            "-af", "adelay=1000", "-c:a", "libmp3lame", "-b:a", "128k",
            str(padded),
        ],
        check=True,
    )
    assert audio_length(padded) > 2.8

    assert run(padded).returncode == 0

    samples = array("h", pcm(padded.with_suffix(".stripped.mp3")))
    first_audible = next(i for i, s in enumerate(samples) if abs(s) > 104)
    # The prepended second is gone, back to the padding and the frame the cut
    # rounds to.
    assert first_audible / RATE <= PADDING + FRAME


def test_id3_tags_survive_stripping(hablar):
    from mutagen.id3 import TIT2, TPE1
    from mutagen.mp3 import MP3

    tagged = MP3(hablar)
    assert tagged.tags is not None
    tagged.tags.add(TIT2(encoding=3, text="hablar"))
    tagged.tags.add(TPE1(encoding=3, text="Vocabulary Deck"))
    tagged.save()

    run(hablar)

    stripped = MP3(hablar.with_suffix(".stripped.mp3")).tags
    assert stripped is not None
    assert stripped["TIT2"].text == ["hablar"]
    assert stripped["TPE1"].text == ["Vocabulary Deck"]


def test_the_muxer_rewrites_the_encoder_tag(hablar):
    """The one tag that does not survive, pinned so the loss stays visible.

    ffmpeg's mp3 muxer always stamps its own `encoder`. Neither -bitexact
    (which drops every tag) nor an explicit -metadata override prevents it, so
    the sources' only shipped tag is replaced rather than carried.
    """
    from mutagen.mp3 import MP3

    source_tags = MP3(hablar).tags
    assert source_tags is not None
    before = source_tags["TSSE"].text
    assert before == ["Lavf60.16.101"]

    run(hablar)

    stripped_tags = MP3(hablar.with_suffix(".stripped.mp3")).tags
    assert stripped_tags is not None
    assert stripped_tags["TSSE"].text != before


def test_several_sources_are_each_stripped(tmp_path):
    sources = [copy_fixture(name, tmp_path) for name in sorted(UTTERANCE_ENDS)]

    result = run(*sources)

    assert result.returncode == 0, result.stderr
    for source in sources:
        stripped = source.with_suffix(".stripped.mp3")
        assert stripped.exists()
        assert duration(stripped) < duration(source)


def test_reports_the_before_and_after_for_a_source(hablar):
    result = run(hablar)

    # The format agreed during design:
    #   hablar-….mp3  1.92s → 0.69s  (-64%)
    line = result.stdout.strip()
    assert hablar.name in line
    assert "1.92s → 0.69s" in line
    # The sign is explicit, so growth could never read as a saving.
    assert "(-64%)" in line


def test_a_summary_line_closes_a_batch(tmp_path):
    # An explicit batch, so that adding a fixture cannot silently change what
    # this test is asserting about the summary.
    names = [
        "yo-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3",
        "hablar-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3",
        "pretérito-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3",
    ]
    sources = [copy_fixture(name, tmp_path) for name in names]

    result = run(*sources)

    lines = result.stdout.strip().splitlines()
    assert len(lines) == 4, lines
    # 1.04 + 1.92 + 2.48 in, 0.48 + 0.69 + 0.82 out.
    summary = lines[-1]
    assert "3 files" in summary
    assert "5.44s" in summary
    assert "2.00s" in summary
    assert "-63%" in summary


def test_a_single_source_gets_no_summary(hablar):
    # A summary that just restates the one line above it is noise.
    result = run(hablar)

    assert len(result.stdout.strip().splitlines()) == 1


def test_a_directory_source_is_rejected_rather_than_walked(hablar, tmp_path):
    # hablar lives inside tmp_path, so a tool that walked the directory would
    # strip it. Nothing should be produced.
    result = run(tmp_path)

    assert result.returncode != 0
    assert "director" in result.stderr.lower()
    assert str(tmp_path) in result.stderr
    assert not hablar.with_suffix(".stripped.mp3").exists()
    # A clear message, not a stack trace that happens to mention directories.
    assert "Traceback" not in result.stderr


def test_a_rerun_reports_unchanged_rather_than_growth(hablar):
    """A second pass must not nibble, and must not claim the file grew.

    Until ticket 04 this could only be checked numerically — measuring one end
    by decoding and the other by probing made an already stripped file look
    like it had grown. A rerun now short-circuits to `unchanged`, which says
    the same thing more strongly.
    """
    run(hablar)

    result = run("--in-place", hablar.with_suffix(".stripped.mp3"))

    assert "unchanged" in result.stdout
    assert "→" not in result.stdout


def test_in_place_replaces_the_source(hablar):
    result = run("--in-place", hablar)

    assert result.returncode == 0, result.stderr
    assert 0.65 < duration(hablar) < 0.72
    assert not hablar.with_suffix(".stripped.mp3").exists()
    # No temporary file left behind.
    assert [p.name for p in hablar.parent.iterdir()] == [hablar.name]


def test_there_is_no_short_form_for_in_place(hablar):
    # -i means *input* in ffmpeg; typed here by muscle memory it must not
    # silently overwrite the source.
    original = hablar.read_bytes()

    result = run("-i", hablar)

    assert result.returncode != 0
    assert hablar.read_bytes() == original


def test_output_writes_to_the_named_destination(hablar, tmp_path):
    named = tmp_path / "chosen.mp3"

    result = run("-o", named, hablar)

    assert result.returncode == 0, result.stderr
    assert named.exists()
    assert 0.65 < duration(named) < 0.72
    assert not hablar.with_suffix(".stripped.mp3").exists()
    assert duration(hablar) > 1.9


def test_output_overwrites_an_existing_destination(hablar, tmp_path):
    named = tmp_path / "chosen.mp3"
    named.write_bytes(b"not an mp3 at all")

    result = run("-o", named, hablar)

    assert result.returncode == 0, result.stderr
    assert 0.65 < duration(named) < 0.72


def test_output_with_several_sources_is_rejected(tmp_path):
    sources = [copy_fixture(name, tmp_path) for name in sorted(UTTERANCE_ENDS)]
    named = tmp_path / "chosen.mp3"

    result = run("-o", named, *sources)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert not named.exists()
    for source in sources:
        assert not source.with_suffix(".stripped.mp3").exists()


def test_output_with_in_place_is_rejected(hablar, tmp_path):
    original = hablar.read_bytes()

    result = run("-o", tmp_path / "chosen.mp3", "--in-place", hablar)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert hablar.read_bytes() == original
    assert not (tmp_path / "chosen.mp3").exists()


def test_a_destination_that_is_its_own_source_strips_in_place(hablar):
    # Must not truncate the file while reading it.
    result = run("-o", hablar, hablar)

    assert result.returncode == 0, result.stderr
    assert 0.65 < duration(hablar) < 0.72
    assert [p.name for p in hablar.parent.iterdir()] == [hablar.name]


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_a_failed_in_place_write_leaves_the_source_intact(hablar):
    original = hablar.read_bytes()
    hablar.parent.chmod(0o555)
    try:
        result = run("--in-place", hablar)
    finally:
        hablar.parent.chmod(0o755)

    assert result.returncode != 0
    assert hablar.read_bytes() == original


def test_output_through_a_symlink_to_the_source_strips_the_target(hablar):
    # Overwriting the link instead of following it would destroy the link and
    # leave the source unstripped.
    link = hablar.parent / "link.mp3"
    link.symlink_to(hablar.name)

    result = run("-o", link, hablar)

    assert result.returncode == 0, result.stderr
    assert link.is_symlink()
    assert_stripped(hablar)


def test_in_place_through_a_symlink_strips_the_target(hablar):
    link = hablar.parent / "link.mp3"
    link.symlink_to(hablar.name)

    assert run("--in-place", link).returncode == 0

    assert link.is_symlink()
    assert_stripped(hablar)


def test_in_place_keeps_the_source_file_mode(hablar):
    # mkstemp creates at 0600; a careless rename would make the file
    # owner-only.
    hablar.chmod(0o644)

    assert run("--in-place", hablar).returncode == 0

    assert stat.S_IMODE(hablar.stat().st_mode) == 0o644


def test_a_new_destination_takes_the_source_file_mode(hablar):
    hablar.chmod(0o644)

    assert run(hablar).returncode == 0

    stripped = hablar.with_suffix(".stripped.mp3")
    assert stat.S_IMODE(stripped.stat().st_mode) == 0o644


def test_an_overwritten_destination_keeps_its_own_mode(hablar, tmp_path):
    named = tmp_path / "chosen.mp3"
    named.write_bytes(b"placeholder")
    named.chmod(0o600)

    assert run("-o", named, hablar).returncode == 0

    assert stat.S_IMODE(named.stat().st_mode) == 0o600


def test_in_place_handles_several_sources(tmp_path):
    sources = [copy_fixture(name, tmp_path) for name in sorted(UTTERANCE_ENDS)]
    originals = {source: duration(source) for source in sources}

    assert run("--in-place", *sources).returncode == 0

    for source in sources:
        assert duration(source) < originals[source]
        assert not source.with_suffix(".stripped.mp3").exists()


def test_a_silent_source_is_unchanged_and_never_truncated(tmp_path):
    # A file with no utterance is almost certainly a failed generation. Keep
    # it for inspection rather than truncating it to nothing.
    silent = make_silent_mp3(tmp_path / "silent.mp3")
    original = silent.read_bytes()

    result = run(silent)

    assert result.returncode == 0, result.stderr
    assert "unchanged" in result.stdout
    assert silent.read_bytes() == original
    assert silent.with_suffix(".stripped.mp3").read_bytes() == original


def test_an_unchanged_outcome_still_writes_the_destination(tmp_path):
    silent = make_silent_mp3(tmp_path / "silent.mp3")
    named = tmp_path / "chosen.mp3"

    assert run("-o", named, silent).returncode == 0

    # An exact copy, so a batch's output set is complete either way.
    assert named.read_bytes() == silent.read_bytes()


def test_in_place_leaves_an_unchanged_source_untouched(hablar):
    run("--in-place", hablar)
    settled = hablar.stat()

    result = run("--in-place", hablar)

    assert "unchanged" in result.stdout
    assert hablar.stat().st_mtime_ns == settled.st_mtime_ns


def test_a_batch_of_unchanged_sources_exits_zero(tmp_path):
    silents = [make_silent_mp3(tmp_path / f"s{n}.mp3") for n in range(3)]

    result = run(*silents)

    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert all(line.endswith("unchanged") for line in lines), lines


def test_a_second_run_is_byte_identical_to_the_first(hablar):
    run(hablar)
    stripped = hablar.with_suffix(".stripped.mp3")
    first = stripped.read_bytes()

    assert run("--in-place", stripped).returncode == 0

    assert stripped.read_bytes() == first


def test_a_hardlinked_destination_is_recognised_as_the_source(tmp_path):
    # Path inequality is not file inequality: a hard link has a different name
    # and the same inode, and copying a file onto itself raises.
    silent = make_silent_mp3(tmp_path / "silent.mp3")
    hardlink = tmp_path / "hardlink.mp3"
    os.link(silent, hardlink)
    original = silent.read_bytes()

    settled = silent.stat()

    result = run("-o", hardlink, silent)

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert silent.read_bytes() == original
    # Rewriting would rename a fresh file over one of the two names, breaking
    # the link and bumping the mtime, for a file that needed no work.
    assert silent.samefile(hardlink)
    assert silent.stat().st_mtime_ns == settled.st_mtime_ns


def test_an_unchanged_destination_keeps_its_own_mode(tmp_path):
    # The unchanged path must obey the same mode rule as the stripped one.
    silent = make_silent_mp3(tmp_path / "silent.mp3")
    silent.chmod(0o644)
    named = tmp_path / "chosen.mp3"
    named.write_bytes(b"placeholder")
    named.chmod(0o600)

    assert run("-o", named, silent).returncode == 0

    assert stat.S_IMODE(named.stat().st_mode) == 0o600


def test_a_tail_artifact_does_not_defeat_trailing_silence(tmp_path):
    """él ends with 11 stray samples in its final 3.1ms, peaking at -44.7 dBFS.

    Scanning back from the last sample stopped on them immediately, so the
    1.15s of silence in front was never seen and the file was left unchanged.
    """
    source = copy_fixture("él-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3", tmp_path)

    result = run(source)

    assert result.returncode == 0, result.stderr
    assert "unchanged" not in result.stdout
    assert_stripped(source.with_suffix(".stripped.mp3"), seconds=0.366)


def make_artifact_mp3(path, tail_silence=True):
    """A tone bracketed by clicks and silences — several artifacts per end."""
    pieces = ["sine=f=800:d=0.02", "anullsrc=r=44100:cl=mono:d=0.5", "sine=f=440:d=0.5"]
    if tail_silence:
        pieces += ["anullsrc=r=44100:cl=mono:d=0.5", "sine=f=800:d=0.02"]
    inputs = []
    for piece in pieces:
        inputs += ["-f", "lavfi", "-i", piece]
    joined = "".join(f"[{n}:a]" for n in range(len(pieces)))
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", *inputs,
            "-filter_complex", f"{joined}concat=n={len(pieces)}:v=0:a=1[out]",
            "-map", "[out]", "-ac", "1", "-ar", str(RATE),
            "-c:a", "libmp3lame", "-b:a", "128k", str(path),
        ],
        check=True,
    )
    return path


def test_several_artifacts_are_stripped_in_one_run(tmp_path):
    # Shedding one artifact per run would make the tool eat further into the
    # file every time it was run.
    source = make_artifact_mp3(tmp_path / "clicks.mp3")

    assert run("--in-place", source).returncode == 0
    once = source.read_bytes()
    assert run("--in-place", source).returncode == 0

    assert source.read_bytes() == once
    assert duration(source) < 0.7


def test_a_source_of_nothing_but_artifacts_is_unchanged(tmp_path):
    # Inverted bounds here used to hand ffmpeg a backwards cut and crash.
    clicks = tmp_path / "clicks-only.mp3"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "sine=f=800:d=0.02",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=1.0",
            "-f", "lavfi", "-i", "sine=f=800:d=0.02",
            "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
            "-map", "[out]", "-ac", "1", "-ar", str(RATE),
            "-c:a", "libmp3lame", "-b:a", "128k", str(clicks),
        ],
        check=True,
    )
    original = clicks.read_bytes()

    result = run("--in-place", clicks)

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert "unchanged" in result.stdout
    assert clicks.read_bytes() == original


def test_a_missing_source_is_reported(tmp_path):
    result = run(tmp_path / "nope.mp3")

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "nope.mp3" in result.stderr


def test_a_corrupt_source_is_reported(tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"this is not an mp3" * 64)

    result = run(broken)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "broken.mp3" in result.stderr
    assert not broken.with_suffix(".stripped.mp3").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_an_unwritable_destination_is_reported(hablar, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    before = hablar.read_bytes()
    locked.chmod(0o555)
    try:
        result = run("-o", locked / "out.mp3", hablar)
    finally:
        locked.chmod(0o755)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert str(locked / "out.mp3") in result.stderr
    assert hablar.read_bytes() == before
    assert list(locked.iterdir()) == []


def test_one_bad_source_does_not_stop_the_others(hablar, tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not an mp3" * 64)

    result = run(broken, hablar)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "broken.mp3" in result.stderr
    # The good source was still stripped.
    assert_stripped(hablar.with_suffix(".stripped.mp3"))


def test_a_failure_after_the_temporary_exists_cleans_it_up(hablar, tmp_path):
    """Reach the cleanup path, which needs a failure after mkstemp.

    A corrupt source fails in probe_duration, long before any temporary is
    created, so it cannot exercise this. Writing to an existing directory gets
    all the way to the rename before failing.
    """
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    before = hablar.read_bytes()

    result = run("-o", blocked, hablar)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert str(blocked) in result.stderr
    assert hablar.read_bytes() == before
    # The temporary lived in the destination's parent, which is tmp_path.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["blocked", hablar.name]


@pytest.mark.parametrize(
    ("present", "expected"),
    [((), "ffmpeg and ffprobe not found"), (("ffmpeg",), "ffprobe not found")],
)
def test_missing_dependencies_are_reported_by_name(
    present, expected, hablar, tmp_path
):
    """Each required binary is named when absent, including ffprobe alone.

    Asserted on the leading clause, not merely on the name appearing somewhere:
    the message ends with "needs ffmpeg and ffprobe, which ship together", so a
    substring check passes even when the wrong tool is reported missing.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("uv", *present):
        found = shutil.which(name)
        assert found, f"{name} is needed to run this test"
        (bin_dir / name).symlink_to(found)

    result = subprocess.run(
        [str(TOOL), str(hablar)],
        capture_output=True,
        text=True,
        env={"PATH": str(bin_dir), "HOME": os.environ["HOME"]},
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert result.stderr.startswith(expected), result.stderr
    assert not hablar.with_suffix(".stripped.mp3").exists()


def test_a_relative_source_name_starting_with_a_dash_is_handled(hablar):
    # ffprobe takes its input positionally, so "-dash.mp3" was parsed as an
    # option and a perfectly good file was reported as unreadable.
    dashed = hablar.parent / "-dash.mp3"
    dashed.write_bytes(hablar.read_bytes())

    result = subprocess.run(
        [str(TOOL), "--", "-dash.mp3"],
        cwd=hablar.parent,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert_stripped(dashed.with_suffix(".stripped.mp3"))


def test_a_broken_symlink_source_says_so(tmp_path):
    dangling = tmp_path / "dangling.mp3"
    dangling.symlink_to(tmp_path / "gone.mp3")

    result = run(dangling)

    assert result.returncode != 0
    assert "broken symlink" in result.stderr


def test_a_source_that_is_not_a_regular_file_says_so(tmp_path):
    pipe = tmp_path / "pipe.mp3"
    os.mkfifo(pipe)

    result = run(pipe)

    assert result.returncode != 0
    assert "not a regular file" in result.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
def test_an_unreadable_source_says_so(hablar):
    hablar.chmod(0o000)
    try:
        result = run(hablar)
    finally:
        hablar.chmod(0o644)

    assert result.returncode != 0
    assert "not readable" in result.stderr


def test_a_single_failing_source_gets_no_failure_summary(tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not an mp3" * 64)

    result = run(broken)

    assert result.returncode == 1
    assert "sources failed" not in result.stderr


def test_a_lower_threshold_strips_more(hablar, tmp_path):
    default = tmp_path / "default.mp3"
    lenient = tmp_path / "lenient.mp3"

    assert run("-o", default, hablar).returncode == 0
    assert run("--threshold", "-20", "-o", lenient, hablar).returncode == 0

    # At -20 dBFS far more of the audio counts as quiet, so more is stripped.
    assert duration(lenient) < duration(default)


def test_more_padding_keeps_more(hablar, tmp_path):
    # Minimum silence held constant across both runs, so only padding varies —
    # a larger minimum silence run would leave more audio on its own.
    tight = tmp_path / "tight.mp3"
    padded = tmp_path / "padded.mp3"
    fixed = ["--min-silence", "0.4"]

    assert run(*fixed, "--padding", "0.05", "-o", tight, hablar).returncode == 0
    assert run(*fixed, "--padding", "0.3", "-o", padded, hablar).returncode == 0

    assert duration(padded) > duration(tight)


# ADR-0001 fixes the frame at ~26.1ms, so with 50ms of padding the invariant
# demands a minimum silence run above 0.0761224s. These literals come from the
# ADR, not from the implementation's own arithmetic.
@pytest.mark.parametrize(
    ("min_silence", "accepted"),
    [
        ("0.0761224", False),
        ("0.0761225", True),
        ("0.10", True),
    ],
)
def test_the_padding_invariant_is_enforced_at_startup(
    min_silence, accepted, hablar
):
    result = run("--padding", "0.05", "--min-silence", min_silence, hablar)

    if accepted:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode == 2
        assert "Traceback" not in result.stderr
        # Rejected before any source is read.
        assert not hablar.with_suffix(".stripped.mp3").exists()


def test_dry_run_reports_what_a_real_run_would(hablar, tmp_path):
    dry = run("--dry-run", "-o", tmp_path / "out.mp3", hablar)
    real = run("-o", tmp_path / "out.mp3", hablar)

    assert dry.returncode == 0, dry.stderr
    assert real.returncode == 0, real.stderr
    reported = [line for line in dry.stdout.splitlines() if "dry run" not in line]
    assert reported == real.stdout.splitlines()


def test_n_is_short_for_dry_run(hablar):
    short = run("-n", hablar)
    long = run("--dry-run", hablar)

    assert short.returncode == 0, short.stderr
    assert short.stdout == long.stdout
    assert not hablar.with_suffix(".stripped.mp3").exists()


def test_dry_run_says_nothing_was_written(hablar):
    result = run("--dry-run", hablar)

    assert "nothing was written" in result.stdout


@pytest.mark.parametrize("mode", [[], ["--in-place"], ["-o", "chosen.mp3"]])
def test_dry_run_writes_nothing(mode, hablar):
    mode = [str(hablar.parent / m) if m.endswith(".mp3") else m for m in mode]
    listing = sorted(p.name for p in hablar.parent.iterdir())
    settled = hablar.stat().st_mtime_ns

    result = run("--dry-run", *mode, hablar)

    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in hablar.parent.iterdir()) == listing
    assert hablar.stat().st_mtime_ns == settled


def test_dry_run_reports_unchanged_sources(tmp_path):
    silent = make_silent_mp3(tmp_path / "silent.mp3")

    result = run("--dry-run", silent)

    assert result.returncode == 0, result.stderr
    assert "unchanged" in result.stdout
    assert not silent.with_suffix(".stripped.mp3").exists()


def test_dry_run_exit_code_matches_a_real_run(tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not an mp3" * 64)

    assert run("--dry-run", broken).returncode == run(broken).returncode == 1


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_dry_run_reports_an_unwritable_destination(hablar, tmp_path):
    # A preview that reports success for a run certain to fail is worse than
    # no preview at all.
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        dry = run("--dry-run", "-o", locked / "out.mp3", hablar)
        real = run("-o", locked / "out.mp3", hablar)
    finally:
        locked.chmod(0o755)

    assert dry.returncode == real.returncode == 1
    assert "cannot write" in dry.stderr
    assert "Traceback" not in dry.stderr
