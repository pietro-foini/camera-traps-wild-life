import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from gpiozero import MotionSensor
from libcamera import controls
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

load_dotenv(Path(__file__).parent / ".env")

SITE = os.getenv("SITE", "0")
CAPTURE_DIR = os.getenv("CAPTURE_DIR", "./captures")
FILER_URL = os.getenv("FILER_URL")
PIR_PIN = 17
MAX_VIDEO_DURATION_SEC = 30
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

    headers = {
        "Seaweed-Site": SITE,
        "Seaweed-Duration": str(round(get_video_duration(filepath))),
    }
    path = Path(filepath)
    with path.open("rb") as f:
        response = requests.post(
            url=f"{FILER_URL}/{path.name}",
            files={"file": (path.name, f, mime_type)},
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()

    print("File uploaded to seaweed!")


def capture_video_while_motion(pir: MotionSensor, picam2: Picamera2, encoder: H264Encoder) -> str:
    """Capture video instantaneously while motion is active"""

    os.makedirs(CAPTURE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(CAPTURE_DIR, f"{timestamp}.mp4")

    print(f"Start recording IMMEDIATELY (max {MAX_VIDEO_DURATION_SEC}s)...")

    output = FfmpegOutput(filepath)
    picam2.start_recording(encoder, output)

    start_time = time.time()
    last_motion_time = start_time

    while (time.time() - start_time) < MAX_VIDEO_DURATION_SEC:
        if pir.is_active:
            last_motion_time = time.time()
        else:
            if (time.time() - last_motion_time) >= GRACE_PERIOD_SEC:
                print(f"No signal since {GRACE_PERIOD_SEC}s! Stop recording...")
                break
        time.sleep(0.1)

    picam2.stop_recording()
    return filepath


def main() -> None:
    print("Initializing Camera (one-time setup)...")

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},
        controls={"FrameRate": 20, "AfMode": controls.AfModeEnum.Continuous},
    )
    picam2.configure(video_config)
    picam2.start()

    encoder = H264Encoder(bitrate=10000000)

    pir = MotionSensor(PIR_PIN)
    print(f"Camera & PIR (GPIO {PIR_PIN}) active! Ready for instant recording...")

    try:
        while True:
            pir.wait_for_active()
            print("Activity detected by PIR sensor!")

            filepath = capture_video_while_motion(pir, picam2, encoder)
            upload_to_seaweed(filepath)

            print("Ready for next trigger!")
            time.sleep(1)

    except KeyboardInterrupt:
        print("Camera trap stopped.")
    finally:
        picam2.stop()


if __name__ == "__main__":
    main()
