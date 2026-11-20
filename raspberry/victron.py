import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from bleak import BleakScanner
from dotenv import load_dotenv
from victron_ble.devices import detect_device_type

load_dotenv(Path(__file__).parent / ".env")

SITE = os.environ["SITE"]
VICTRON_MAC = os.environ["VICTRON_MAC"].replace(":", "").upper()
VICTRON_KEY = os.environ["VICTRON_KEY"]
SCAN_TIMEOUT_SEC = 15.0
VICTRON_MANUFACTURER_ID = 0x02E1


async def read_victron_once() -> dict[str, Any] | None:
    """Scans BLE advertisements and decodes a single Victron Instant Readout packet"""

    found = asyncio.Event()
    result: dict[str, Any] = {}

    def callback(device: Any, adv_data: Any) -> None:
        if device.address.replace(":", "").upper() != VICTRON_MAC or found.is_set():
            return

        raw = adv_data.manufacturer_data.get(VICTRON_MANUFACTURER_ID)
        if not raw or not raw.startswith(b"\x10"):
            return

        parser_cls = detect_device_type(raw)
        if not parser_cls:
            return

        try:
            parsed = parser_cls(VICTRON_KEY).parse(raw)
            charge_state = parsed.get_charge_state()
            result.update(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "state": getattr(charge_state, "name", str(charge_state)),
                    "battery_v": parsed.get_battery_voltage(),
                    "battery_a": parsed.get_battery_charging_current(),
                    "solar_w": parsed.get_solar_power(),
                    "yield_wh": parsed.get_yield_today(),
                    "load_a": parsed.get_external_device_load(),
                }
            )
            found.set()
        except Exception as e:
            print(f"Error decoding Victron BLE packet: {e}")
            found.set()

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    try:
        await asyncio.wait_for(found.wait(), timeout=SCAN_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        pass
    finally:
        await scanner.stop()

    return result if result else None


def main() -> None:
    print(f"Reading Victron status for site '{SITE}'...")
    data = asyncio.run(read_victron_once())

    if not data:
        print(f"No BLE signal received within {SCAN_TIMEOUT_SEC}s.")
        sys.exit(1)

    print(f"Timestamp : {data['timestamp']}")
    print(f"State     : {data['state']}")
    print(f"Battery   : {data['battery_v']} V ({data['battery_a']} A)")
    print(f"Solar     : {data['solar_w']} W (Today: {data['yield_wh']} Wh)")
    print(f"Load      : {data['load_a']} A")


if __name__ == "__main__":
    main()
