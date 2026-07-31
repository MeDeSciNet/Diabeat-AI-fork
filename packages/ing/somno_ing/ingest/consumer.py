"""MQTT consumer (PRD 6.1 ING-1).

Subscribes to ``somno/+/signal`` and ``somno/+/control``. Sessions are opened by
a control message and closed by one; analysis is handed to Celery so the
consumer never blocks on a long batch job.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from urllib.parse import urlparse

from ..db import Device, Session as SessionRow, db_session
from ..settings import get_settings
from . import SessionIngestor

log = logging.getLogger(__name__)

SIGNAL_TOPIC = "somno/+/signal"
CONTROL_TOPIC = "somno/+/control"


class IngestService:
    def __init__(self, on_session_closed=None) -> None:
        self.sessions: dict[str, SessionIngestor] = {}
        self.lock = threading.Lock()
        self.on_session_closed = on_session_closed or _default_close_handler

    # ------------------------------------------------------------- handlers
    def handle(self, topic: str, payload: dict) -> None:
        if topic.endswith("/control"):
            self.handle_control(payload)
        else:
            self.handle_signal(payload)

    def handle_control(self, payload: dict) -> None:
        event = payload.get("event")
        session_id = payload["session_id"]
        if event == "session_start":
            with self.lock:
                self.sessions[session_id] = SessionIngestor(
                    session_id=session_id,
                    device_id=payload["device_id"],
                    subject_code=payload.get("subject_code", "SUBJ-UNKNOWN"),
                    bed_id=payload.get("bed_id"),
                    scenario=payload.get("scenario"),
                    seed=payload.get("seed"),
                    duration_ms=payload.get("duration_ms"),
                    sample_rates=payload.get("sample_rates", {}),
                    psg=payload.get("psg"),
                )
            _upsert_session_row(payload)
            log.info("session %s opened (device %s)", session_id, payload["device_id"])
        elif event == "session_end":
            with self.lock:
                ing = self.sessions.pop(session_id, None)
            if ing is None:
                log.warning("session_end for unknown session %s", session_id)
                return
            log.info("session %s closed after %d chunks", session_id, ing.chunks_received)
            self.on_session_closed(ing)

    def handle_signal(self, payload: dict) -> None:
        session_id = payload["session_id"]
        with self.lock:
            ing = self.sessions.get(session_id)
        if ing is None:
            # Chunks before the control message, or after a consumer restart.
            # Opening implicitly keeps the recording rather than dropping it.
            ing = SessionIngestor(session_id=session_id, device_id=payload["device_id"])
            with self.lock:
                self.sessions[session_id] = ing
        ing.on_chunk(payload)
        _touch_device(payload)

    # ----------------------------------------------------------------- loop
    def run_forever(self) -> None:  # pragma: no cover - needs a broker
        import paho.mqtt.client as mqtt

        url = urlparse(get_settings().mqtt_url)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)

        def on_connect(c, userdata, flags, reason_code, properties=None):
            log.info("connected to broker: %s", reason_code)
            c.subscribe([(SIGNAL_TOPIC, 1), (CONTROL_TOPIC, 1)])

        def on_message(c, userdata, msg):
            try:
                self.handle(msg.topic, json.loads(msg.payload))
            except Exception:
                log.exception("failed to handle message on %s", msg.topic)

        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(url.hostname or "localhost", url.port or 1883, keepalive=60)
        client.loop_forever()


def _default_close_handler(ing: SessionIngestor) -> None:
    from ..pipeline import persist_ingest
    from ..tasks import analyze_session

    persist_ingest(ing)
    analyze_session.delay(ing.session_id)


def _upsert_session_row(payload: dict) -> None:
    with db_session() as db:
        row = db.get(SessionRow, payload["session_id"])
        if row is None:
            row = SessionRow(id=payload["session_id"], subject_code="SUBJ-UNKNOWN")
            db.add(row)
        row.subject_code = payload.get("subject_code", row.subject_code)
        row.device_id = payload["device_id"]
        row.bed_id = payload.get("bed_id")
        row.scenario = payload.get("scenario")
        row.seed = payload.get("seed")
        row.duration_ms = payload.get("duration_ms")
        row.sample_rates = payload.get("sample_rates", {})
        row.status = "recording"
        row.started_at = datetime.now(UTC)


def _touch_device(payload: dict) -> None:
    state = payload.get("device_state") or {}
    if not state or payload.get("seq", 0) % 20:
        return  # device telemetry every ~20 chunks is plenty
    with db_session() as db:
        dev = db.get(Device, payload["device_id"])
        if dev is None:
            dev = Device(device_id=payload["device_id"])
            db.add(dev)
        dev.last_seen_at = datetime.now(UTC)
        dev.battery_pct = state.get("battery_pct")
        dev.storage_free_pct = state.get("storage_free_pct")
        dev.electrode_ok = state.get("electrode_ok")
