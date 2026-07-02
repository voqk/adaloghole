"""Webcam Sensor — Python + OpenCV, the Phase 1 reference Sensor.

Grabs a frame from /dev/video<N> on a cadence and POSTs it as raw JPEG to the
Brain's /frame endpoint over localhost HTTP (the same wire binding a remote
Phase 3 sensor uses). The cadence is re-read from GET /settings every loop, so
portal edits to sample_interval_s apply on the next frame without a restart.

Runs either as a daemon thread inside the server process (autostart = true in
adaloghole.toml) or standalone against a running server:

    python -m app.roles.sensor.webcam --server http://127.0.0.1:8000 --device 0

Failure policy: camera-open failures and failed POSTs log and retry with
backoff; the loop never dies on its own.
"""

import argparse
import logging
import threading
import time

import cv2
import httpx

from ...registry import register

logger = logging.getLogger("uvicorn.error")

_MAX_BACKOFF_S = 30.0
_POST_TIMEOUT_S = 90.0  # classification can take seconds; never race it


@register("sensor", "webcam")
class WebcamSensor:
    def __init__(self, brain_url: str, device: int = 0, width: int = 1280,
                 height: int = 720, jpeg_quality: int = 85, source_id: str | None = None):
        self.brain_url = brain_url.rstrip("/")
        self.device = device
        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self.source_id = source_id or f"webcam-{device}"
        self._cap: cv2.VideoCapture | None = None
        self._seq = 0
        self._interval_s = 10.0  # fallback until /settings answers

    # --- Capture loop -----------------------------------------------------------

    def run(self, stop: threading.Event) -> None:
        client = httpx.Client(timeout=_POST_TIMEOUT_S)
        failures = 0
        try:
            while not stop.is_set():
                ok = self._tick(client)
                failures = 0 if ok else failures + 1
                # Normal cadence on success; exponential backoff while broken.
                wait = self._interval_s if ok else min(_MAX_BACKOFF_S, 2.0 ** failures)
                stop.wait(wait)
        finally:
            client.close()
            self._release()

    def _tick(self, client: httpx.Client) -> bool:
        """One capture->classify round trip. Returns False on any failure."""
        self._refresh_interval(client)
        frame = self._grab()
        if frame is None:
            return False
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            logger.warning("[sensor:webcam] JPEG encode failed")
            return False
        self._seq += 1
        headers = {
            "Content-Type": "image/jpeg",
            "X-Adaloghole-Source-Id": self.source_id,
            "X-Adaloghole-Ts": str(time.time()),
            "X-Adaloghole-Seq": str(self._seq),
            "X-Adaloghole-Width": str(frame.shape[1]),
            "X-Adaloghole-Height": str(frame.shape[0]),
        }
        try:
            resp = client.post(f"{self.brain_url}/frame", content=buf.tobytes(), headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("[sensor:webcam] POST /frame failed: %s", e)
            return False
        body = resp.json()
        verdict, status = body["verdict"], body["status"]
        logger.info(
            "[sensor:webcam] #%d %s (%.2f) -> av_state=%s mode=%s",
            self._seq, verdict["label"], verdict["confidence"],
            status["av_state"], status["mode"],
        )
        return True

    # --- Camera handling ----------------------------------------------------------

    def _grab(self):
        cap = self._ensure_camera()
        if cap is None:
            return None
        ok, frame = cap.read()
        if not ok or frame is None:
            logger.warning("[sensor:webcam] frame grab failed; reopening /dev/video%d", self.device)
            self._release()
            return None
        return frame

    def _ensure_camera(self) -> cv2.VideoCapture | None:
        if self._cap is not None and self._cap.isOpened():
            return self._cap
        cap = cv2.VideoCapture(self.device)
        if not cap.isOpened():
            logger.warning("[sensor:webcam] cannot open /dev/video%d", self.device)
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        for _ in range(3):  # let auto-exposure settle on a fresh open
            cap.read()
        self._cap = cap
        logger.info("[sensor:webcam] opened /dev/video%d (%dx%d requested)",
                    self.device, self.width, self.height)
        return cap

    def _release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # --- Cadence -------------------------------------------------------------------

    def _refresh_interval(self, client: httpx.Client) -> None:
        """The Brain owns the Settings; the Sensor owns the timer. Re-read the
        interval each loop so portal edits apply without a restart."""
        try:
            resp = client.get(f"{self.brain_url}/settings", timeout=5.0)
            resp.raise_for_status()
            self._interval_s = max(0.5, float(resp.json()["sample_interval_s"]))
        except (httpx.HTTPError, KeyError, ValueError):
            pass  # keep the last known cadence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the webcam sensor against a running Brain.")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="Brain base URL")
    parser.add_argument("--device", type=int, default=0, help="/dev/video index")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sensor = WebcamSensor(
        brain_url=args.server, device=args.device, width=args.width,
        height=args.height, jpeg_quality=args.jpeg_quality,
    )
    stop = threading.Event()
    try:
        sensor.run(stop)
    except KeyboardInterrupt:
        stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
