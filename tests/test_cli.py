"""Seam 1: the CLI, invoked as a subprocess against real ffmpeg."""

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
