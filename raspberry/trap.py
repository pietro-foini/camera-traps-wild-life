import os
import shutil
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
from picamera2.outputs import FileOutput

load_dotenv(Path(__file__).parent / ".env")

SITE = os.getenv("SITE", "0")
CAPTURE_DIR = os.getenv("CAPTURE_DIR", "/dev/shm/captures")
FILER_URL = os.getenv("FILER_URL")
PIR_PIN = 17
MAX_VIDEO_DURATION_SEC = 30
GRACE_PERIOD_SEC = 5
FPS = 20


def upload_to_seaweed(filepath: str, duration: float, mime_type: str = "video/mp4") -> bool:
    """Uploads a file to seaweed"""

    headers = {
        "Seaweed-Site": SITE,
        "Seaweed-Duration": str(round(duration)),
    }
    path = Path(filepath)
    try:
        with path.open("rb") as f:
            response = requests.post(
                url=f"{FILER_URL}/{path.name}",
                files={"file": (path.name, f, mime_type)},
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
        print("File uploaded to seaweed!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error during the uploading: {e}")
        return False


def capture_video_while_motion(pir: MotionSensor, picam2: Picamera2, encoder: H264Encoder) -> tuple[str, float]:
    """Start up camera, capture video until motion is detected and then turn off camera"""

    os.makedirs(CAPTURE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    h264_path = os.path.join(CAPTURE_DIR, f"{timestamp}.h264")
    mp4_path = os.path.join(CAPTURE_DIR, f"{timestamp}.mp4")

    picam2.start()
    time.sleep(0.5)

    print(f"Start recording (max {MAX_VIDEO_DURATION_SEC}s)...")
    output = FileOutput(h264_path)
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
    duration = time.time() - start_time
    picam2.stop()

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", h264_path, "-c", "copy", mp4_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    os.remove(h264_path)

    return mp4_path, duration


def main() -> None:
    print("Initializing Camera configuration...")

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},
        controls={"FrameRate": FPS, "AfMode": controls.AfModeEnum.Continuous},
        buffer_count=6,
    )
    picam2.configure(video_config)

    encoder = H264Encoder(bitrate=5000000, repeat=True)

    pir = MotionSensor(PIR_PIN, queue_len=1)
    print(f"PIR (GPIO {PIR_PIN}) active! Camera in low-power standby. Waiting for motion...")

    try:
        while True:
            pir.wait_for_active()
            print("Activity detected by PIR sensor!")

            filepath, duration = capture_video_while_motion(pir, picam2, encoder)

            if upload_to_seaweed(filepath, duration):
                os.remove(filepath)
            else:
                backup_dir = "/backup_videos"
                os.makedirs(backup_dir, exist_ok=True)
                shutil.move(filepath, os.path.join(backup_dir, os.path.basename(filepath)))

            print("Ready for next trigger!")
            time.sleep(1)

    except KeyboardInterrupt:
        print("Camera trap stopped.")
    finally:
        picam2.close()


if __name__ == "__main__":
    main()
