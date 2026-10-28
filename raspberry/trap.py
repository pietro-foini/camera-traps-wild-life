import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from gpiozero import MotionSensor

load_dotenv(Path(__file__).parent / ".env")

CAPTURE_DIR = os.getenv("CAPTURE_DIR", "./captures")  # Local path for storing videos
FILER_URL = os.getenv("FILER_URL")  # Seaweed url server for uploading videos
PIR_PIN = 17  # GPIO 17 (corresponds to physical Pin 11)
VIDEO_DURATION_MS = 10000


def upload_to_seaweed(filepath: str, mime_type: str = "video/mp4") -> None:
    """Uploads a file to seaweed"""

    headers = {"Seaweed-Site": "0", "Seaweed-Duration": "7"}  # TODO  # TODO

    path = Path(filepath)
    with path.open("rb") as f:
        response = requests.post(
            url=f"{FILER_URL}/{path.name}", files={"file": (path.name, f, mime_type)}, headers=headers, timeout=120
        )
        response.raise_for_status()


def capture_video() -> str:
    """Captures a video"""

    os.makedirs(CAPTURE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(CAPTURE_DIR, f"trap_{timestamp}.mp4")

    print(f"Recording {VIDEO_DURATION_MS // 1000}s video...")

    subprocess.run(
        [
            "rpicam-vid",
            "-t",
            str(VIDEO_DURATION_MS),
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
        ],
        check=True,
    )

    print(f"Video saved: {filepath}")

    return filepath


def on_motion_detected() -> None:
    """Callback triggered automatically when the PIR sensor detects motion"""

    print("Activity detected by PIR sensor!")

    # filepath = capture_video()
    # upload_to_seaweed(filepath)


def on_motion_stopped() -> None:
    """Callback triggered when the sensor returns to an idle state"""

    print("Motion stopped. Waiting for next trigger...")


def main() -> None:
    print(f"Starting Camera Trap (GPIO Pin: {PIR_PIN})")

    pir = MotionSensor(PIR_PIN)

    # Bind sensor events to our callback functions
    pir.when_motion = on_motion_detected
    pir.when_no_motion = on_motion_stopped

    print("PIR sensor active. Listening 24/7 (Press Ctrl+C to stop)...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Camera trap stopped.")


if __name__ == "__main__":
    main()
