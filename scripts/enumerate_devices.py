"""List configured devices without marking unseen hardware online."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.drivers.camera_pi import default_cameras
from app.drivers.respeaker import device_report
from app.drivers.serial_bridge import bridge_status
from app.vision.aruco import aruco_backend_status


def main() -> int:
    print("cameras:")
    for camera in default_cameras():
        print(f"  {camera['camera_id']}: {camera['state']} ({camera['error']})")
    audio = device_report()
    serial = bridge_status()
    vision = aruco_backend_status()
    print(f"xvf3800: {audio['state']} {audio['error']}")
    print(f"serial: {serial['state']} {serial['reason']}")
    print(f"aruco: {vision['status']} {vision['reason']}")
    print("No device was marked live by this enumeration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
