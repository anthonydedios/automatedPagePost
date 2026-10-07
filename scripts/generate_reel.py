"""
Turns a batch of product photos into a vertical (9:16) slideshow video
with a slow zoom on each photo, suitable for uploading as a Facebook Reel.

Can be run standalone for testing:
    python scripts/generate_reel.py photo1.jpg photo2.jpg --output out.mp4

Used as a module by scripts/post_reel.py for the actual automated run.
"""

import os
import random
import subprocess
import sys
import tempfile

WIDTH, HEIGHT = 1080, 1920
SECONDS_PER_PHOTO = 2.5
FPS = 30
AUDIO_DIR = "audio"
AUDIO_EXTENSIONS = {".mp3", ".aac", ".m4a", ".wav"}


def build_segment(photo_path, out_path):
    """
    Renders one photo into a short vertical video clip with a slow zoom,
    scaled/cropped to completely fill 1080x1920 (no letterboxing).
    """
    frames = int(SECONDS_PER_PHOTO * FPS)
    filter_chain = (
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH*2}:{HEIGHT*2},"
        f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"setsar=1"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", photo_path,
        "-vf", filter_chain,
        "-t", str(SECONDS_PER_PHOTO),
        "-pix_fmt", "yuv420p",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_segments(segment_paths, output_path):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for seg in segment_paths:
            f.write(f"file '{os.path.abspath(seg)}'\n")
        list_path = f.name

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.unlink(list_path)


def pick_random_audio_track():
    """
    Returns a random audio file path from AUDIO_DIR, or None if that
    folder doesn't exist or has no audio files - callers should treat
    None as "generate a silent reel".
    """
    if not os.path.isdir(AUDIO_DIR):
        return None
    tracks = [
        os.path.join(AUDIO_DIR, f)
        for f in os.listdir(AUDIO_DIR)
        if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS
    ]
    return random.choice(tracks) if tracks else None


def add_music(video_path, audio_path, output_path, duration):
    """
    Loops/trims audio_path to exactly cover `duration` seconds of
    video_path, with a 1-second fade-out at the end, and muxes it onto
    the (currently silent) video.
    """
    fade_start = max(duration - 1, 0)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", audio_path,
        "-filter_complex", f"[1:a]afade=t=out:st={fade_start}:d=1[aout]",
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        "-t", str(duration),
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_reel(photo_paths, output_path, audio_path=None):
    """
    Builds a slideshow mp4 from photo_paths (in the order given).
    If audio_path is given, that track is looped/trimmed under the
    video. If audio_path is None, picks a random track from AUDIO_DIR
    automatically (or stays silent if that folder is empty/missing).
    """
    duration = len(photo_paths) * SECONDS_PER_PHOTO

    with tempfile.TemporaryDirectory() as tmpdir:
        segments = []
        for i, photo in enumerate(photo_paths):
            seg_path = os.path.join(tmpdir, f"seg_{i:03d}.mp4")
            build_segment(photo, seg_path)
            segments.append(seg_path)

        silent_path = os.path.join(tmpdir, "silent.mp4")
        concat_segments(segments, silent_path)

        if audio_path is None:
            audio_path = pick_random_audio_track()

        if audio_path:
            print(f"Adding music track: {audio_path}")
            add_music(silent_path, audio_path, output_path, duration)
        else:
            print("No audio tracks found in audio/ - generating a silent reel.")
            os.replace(silent_path, output_path)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("photos", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        generate_reel(args.photos, args.output)
    except subprocess.CalledProcessError as e:
        print("ffmpeg failed:", e.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        sys.exit(1)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    duration = len(args.photos) * SECONDS_PER_PHOTO
    print(f"Reel generated: {args.output} ({size_mb:.1f} MB, {duration:.1f}s)")


if __name__ == "__main__":
    main()
