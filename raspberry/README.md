# Raspberry Pi Camera Trap

A motion-triggered camera trap for the Raspberry Pi Zero 2W. A PIR sensor wakes the camera when motion is detected, the 
video is recorded (up to 30 seconds), and then uploaded to a SeaweedFS filer. If the upload fails, the video is saved 
locally as a backup.

## Requirements

- Raspberry Pi Zero 2W with Raspberry Pi OS
- Camera module (connected to the Pi)
- PIR motion sensor (connected to GPIO 17)
- A reachable SeaweedFS filer
- Victron SmartSolar MPPT charge controller (optional, for BLE solar/battery telemetry)

> **Note:** the camera and the PIR sensor must be physically connected to the Raspberry Pi before running the script.

## 1. Install the operating system

Install the OS on the micro SD card from your computer by following the instructions at: https://www.raspberrypi.com/software/.

## 2. Connect to the Raspberry Pi

To configure the Raspberry Pi Zero 2W over Wi-Fi you can use [PuTTY](https://www.putty.org/) (SSH):

1. Insert the micro SD card and power on the Pi. The first boot takes a while, as the system finishes installing.
2. Open PuTTY and enter the **hostname** (or device name) of the Raspberry Pi, or its **IP address**. If the Pi is connected to a phone hotspot, you can find the IP address in the hotspot's connected devices list.
3. Log in. You now have a terminal on the Raspberry Pi.

Python is already installed. You may need to install Git:

```bash
sudo apt update
sudo apt install git -y
```

## 3. Clone the repository

```bash
git clone https://github.com/pietro-foini/camera-traps-wild-life
```

## 4. Install system dependencies

```bash
sudo apt install -y python3-picamera2 python3-libcamera python3-gpiozero python3-lgpio ffmpeg libcap-dev bluez tmux
```

## 5. Create the Python virtual environment

The `--system-site-packages` flag is required so the venv can access the system-installed `picamera2` and `libcamera` packages.

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

Install the Python requirements:

```bash
pip install -r requirements.txt
```

## 6. Configure environment variables

Create a `.env` file in the same folder as `trap.py` and `victron.py`:

| Variable      | Required | Description                                          |
|---------------|----------|------------------------------------------------------|
| `SITE`        | Yes      | Name of the site where the camera trap is installed  |
| `LATITUDE`    | Yes      | Latitude of the camera trap                          |
| `LONGITUDE`   | Yes      | Longitude of the camera trap                         |
| `FILER_URL`   | Yes      | URL of the SeaweedFS filer used for uploads          |
| `VICTRON_MAC` | Yes      | Bluetooth MAC address of the Victron SmartSolar      |
| `VICTRON_KEY` | Yes      | Instant Readout key from the VictronConnect app      |


## 7. Run the scripts

```bash
python3 trap.py
```

or

```bash
python3 victron.py
```

## How it works

1. The camera stays in low-power standby while waiting for the PIR sensor (GPIO 17).
2. On motion, it records 1080p H.264 video at 20 FPS, saved as MP4.
3. Recording stops after **5 seconds** without motion, or after a maximum of **30 seconds**.
4. The video is uploaded to SeaweedFS together with site, coordinates and duration as headers.
5. On success, the local file is deleted. On failure, it is moved to `/backup_videos`.

The main settings (`MAX_VIDEO_DURATION_SEC`, `GRACE_PERIOD_SEC`, `FPS`, `PIR_PIN`) can be changed at the top of `trap.py`.

Press `Ctrl+C` to stop the script.