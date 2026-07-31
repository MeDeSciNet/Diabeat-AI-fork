"""Chunk encoding and transports.

The wire format is deliberately the one a real patch would use - int16 samples,
base64 in a small JSON envelope, one topic per device - so that swapping SIM for
hardware changes nothing downstream.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .signals import CHANNEL_SCALE, CHANNEL_UNITS

SIGNAL_TOPIC = "somno/{device_id}/signal"
CONTROL_TOPIC = "somno/{device_id}/control"


def encode_chunk(
    device_id: str,
    session_id: str,
    seq: int,
    t_start_ms: int,
    duration_ms: int,
    channels: dict[str, np.ndarray],
    fs: dict[str, float],
    device_state: dict | None = None,
) -> dict:
    payload = {
        "device_id": device_id,
        "session_id": session_id,
        "seq": seq,
        "t_start_ms": int(t_start_ms),
        "duration_ms": int(duration_ms),
        "channels": {},
    }
    for name, data in channels.items():
        scale = CHANNEL_SCALE[name]
        q = np.clip(np.round(np.asarray(data) / scale), -32768, 32767).astype("<i2")
        payload["channels"][name] = {
            "fs_hz": fs[name],
            "scale": scale,
            "unit": CHANNEL_UNITS[name],
            "data_b64": base64.b64encode(q.tobytes()).decode("ascii"),
        }
    if device_state is not None:
        payload["device_state"] = device_state
    return payload


def decode_channel(ch: dict) -> np.ndarray:
    raw = np.frombuffer(base64.b64decode(ch["data_b64"]), dtype="<i2")
    return raw.astype(np.float64) * ch["scale"]


class Publisher(Protocol):
    def publish(self, topic: str, payload: dict) -> None: ...
    def close(self) -> None: ...


class NullPublisher:
    """Generate and discard - used for benchmarking the synthesis path alone."""

    def publish(self, topic: str, payload: dict) -> None:  # noqa: D102
        return

    def close(self) -> None:  # noqa: D102
        return


class CallbackPublisher:
    """In-process transport. Lets tests drive ING without a broker."""

    def __init__(self, fn: Callable[[str, dict], None]) -> None:
        self.fn = fn

    def publish(self, topic: str, payload: dict) -> None:
        self.fn(topic, payload)

    def close(self) -> None:
        return


class FilePublisher:
    """Newline-delimited JSON on disk - stands in for the device's microSD card."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("w")

    def publish(self, topic: str, payload: dict) -> None:
        self.fh.write(json.dumps({"topic": topic, "payload": payload}) + "\n")

    def close(self) -> None:
        self.fh.close()


class MqttPublisher:
    def __init__(self, url: str, client_id: str, qos: int = 1) -> None:
        import paho.mqtt.client as mqtt
        from urllib.parse import urlparse

        u = urlparse(url)
        self.qos = qos
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv5
        )
        if u.username:
            self.client.username_pw_set(u.username, u.password or "")
        self.client.max_queued_messages_set(0)
        self.client.connect(u.hostname or "localhost", u.port or 1883, keepalive=60)
        self.client.loop_start()

    def publish(self, topic: str, payload: dict) -> None:
        info = self.client.publish(topic, json.dumps(payload), qos=self.qos)
        # Back-pressure: an 8-hour night is ~1.4 GB, far more than the client
        # will happily buffer if the broker or ING falls behind.
        deadline = time.monotonic() + 30
        while not info.is_published() and time.monotonic() < deadline:
            time.sleep(0.002)

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


def make_publisher(target: str, client_id: str, out_dir: Path | None = None) -> Publisher:
    if target in ("none", "null"):
        return NullPublisher()
    if target.startswith("file:"):
        return FilePublisher(Path(target[5:]))
    if target == "file" and out_dir is not None:
        return FilePublisher(out_dir / "stream.ndjson")
    if target.startswith("mqtt://") or target.startswith("mqtts://"):
        return MqttPublisher(target, client_id)
    raise ValueError(f"unsupported publish target: {target!r}")
