"""ffmpeg helpers: locate the binaries, stream raw frames into H.264, mux audio, probe files."""
import json
import shutil
import subprocess

INSTALL_HINT = ("Install ffmpeg and make sure it is on PATH: Windows 'winget install Gyan.FFmpeg', "
                "macOS 'brew install ffmpeg', Debian/Ubuntu 'sudo apt install ffmpeg'.")


def find_tool(name: str = "ffmpeg") -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} not found. {INSTALL_HINT}")
    return path


class FrameWriter:
    """Pipes raw RGB frames into ffmpeg (libx264, yuv420p)."""

    def __init__(self, path: str, size: tuple[int, int], fps: int, crf: int = 20, preset: str = "veryfast"):
        w, h = size
        self.proc = subprocess.Popen(
            [find_tool(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", path],
            stdin=subprocess.PIPE)

    def write(self, rgb: bytes) -> None:
        self.proc.stdin.write(rgb)

    def close(self) -> None:
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError("ffmpeg failed while encoding video")


def mux(video: str, wav: str, out: str, audio_bitrate: str = "160k") -> None:
    """Combine a silent video and a WAV into a web-ready MP4 (AAC audio, faststart)."""
    subprocess.run([find_tool(), "-y", "-loglevel", "error", "-i", video, "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", audio_bitrate, "-shortest",
                    "-movflags", "+faststart", out], check=True)


def probe(path: str) -> dict:
    """Width, height and duration (seconds) of a video file."""
    res = subprocess.run([find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height:format=duration", "-of", "json", path],
                         check=True, capture_output=True, text=True)
    data = json.loads(res.stdout)
    stream = data["streams"][0]
    return {"width": int(stream["width"]), "height": int(stream["height"]),
            "duration": float(data["format"]["duration"])}


def grab_frame(path: str, t: float, size: tuple[int, int]) -> bytes:
    """One frame at time t, scaled to size, as raw RGB bytes."""
    w, h = size
    res = subprocess.run([find_tool(), "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         check=True, capture_output=True)
    return res.stdout
