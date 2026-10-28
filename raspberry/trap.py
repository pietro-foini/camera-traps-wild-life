import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from gpiozero import MotionSensor

load_dotenv(Path(__file__).parent / ".env")

SITE = os.getenv("SITE", "0")  # Name of the current site.
CAPTURE_DIR = os.getenv("CAPTURE_DIR", "./captures")  # Local path for storing videos
FILER_URL = os.getenv("FILER_URL")  # Seaweed url server for uploading videos
PIR_PIN = 17  # GPIO 17 (corresponds to physical Pin 11)
MAX_VIDEO_DURATION_MS = 30000  # Max duration: 30 seconds.
GRACE_PERIOD_SEC = 5


def get_video_duration(filepath: str) -> float:
    """Get video duration in seconds."""

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filepath,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def upload_to_seaweed(filepath: str, mime_type: str = "video/mp4") -> None:
    """Uploads a file to seaweed"""

    headers = {"Seaweed-Site": SITE, "Seaweed-Duration": str(round(get_video_duration(filepath)))}

    path = Path(filepath)
    with path.open("rb") as f:
        response = requests.post(
            url=f"{FILER_URL}/{path.name}", files={"file": (path.name, f, mime_type)}, headers=headers, timeout=120
        )
        response.raise_for_status()


def capture_video_while_motion(pir: MotionSensor) -> str:
    """Capture video while motion"""

    os.makedirs(CAPTURE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(CAPTURE_DIR, f"{timestamp}.mp4")

    print(f"Start recording (max {MAX_VIDEO_DURATION_MS // 1000}s)...")

    process = subprocess.Popen(
        [
            "rpicam-vid",
            "-t",
            str(MAX_VIDEO_DURATION_MS),
            "-o",
            filepath,
            "--codec",
            "libav",
            "--width",
            "1920",
            "--height",
            "1080",
            "--framerate",
            "30",
            "--autofocus-mode",
            "continuous",
            "--nopreview",
        ]
    )

    last_motion_time = time.time()

    while process.poll() is None:
        if pir.is_active:
            last_motion_time = time.time()
        else:
            seconds_without_motion = time.time() - last_motion_time
            if seconds_without_motion >= GRACE_PERIOD_SEC:
                print(f"No signal since {GRACE_PERIOD_SEC}s! Stop recording...")
                process.send_signal(signal.SIGINT)
                break

        time.sleep(0.2)

    process.wait()

    return filepath


def main() -> None:
    print(f"Starting Camera Trap (GPIO Pin: {PIR_PIN})")

    pir = MotionSensor(PIR_PIN)

    print("PIR sensor active. Listening 24/7 (Press Ctrl+C to stop)...")

    try:
        while True:
            pir.wait_for_active()
            print("Activity detected by PIR sensor!")

            # filepath = capture_video_while_motion(pir)
            # upload_to_seaweed(filepath)

            # filepath = capture_video_while_motion(pir)
            filepath = "./captures/test_video.mp4"  # Path to your existing test MP4

            print(f"Uploading {filepath} to SeaweedFS...")
            upload_to_seaweed(filepath)
            print("Upload completed successfully!")

            # Wait for the PIR sensor to go back to idle before allowing a new trigger
            print("Waiting for motion to stop...")
            pir.wait_for_inactive()
            print("Ready for next trigger!")

            time.sleep(1)

    except KeyboardInterrupt:
        print("Camera trap stopped.")


if __name__ == "__main__":
    main()
