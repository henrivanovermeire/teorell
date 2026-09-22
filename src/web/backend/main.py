"""FastAPI WebSocket server for live teorell sessions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from teorell_core import (
    DESFLURANE,
    HALOTHANE,
    ISOFLURANE,
    LiveSession,
    Patient,
    SEVOFLURANE,
    Sex,
)

AGENTS = {
    "sevoflurane": SEVOFLURANE,
    "isoflurane": ISOFLURANE,
    "desflurane": DESFLURANE,
    "halothane": HALOTHANE,
}

LIVE_SIM_MIN_PER_WALL_S = 1.0 / 60.0

app = FastAPI(title="teorell-live", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _patient_from(msg: dict[str, Any]) -> Patient:
    sex_raw = str(msg.get("sex", "male")).lower()
    sex = Sex.FEMALE if sex_raw.startswith("f") else Sex.MALE
    return Patient(
        age=float(msg.get("age", 40)),
        weight=float(msg.get("weight", 70)),
        height=float(msg.get("height", 170)),
        sex=sex,
    )


@app.websocket("/ws")
async def live_ws(ws: WebSocket) -> None:
    await ws.accept()
    session: LiveSession | None = None
    playing = False
    # Live playback: 1 wall-second → 1 simulation-second.
    sim_min_per_wall_s = LIVE_SIM_MIN_PER_WALL_S
    prediction_window_min = 60.0
    prediction_step_min = 0.5
    wall_tick_s = 0.1
    tick_task: asyncio.Task[None] | None = None
    # Serialize mutations: ticker to_thread vs bolus/reset on the same session.
    session_lock = asyncio.Lock()

    async def send(payload: dict[str, Any]) -> None:
        await ws.send_text(json.dumps(payload))

    def prediction_for(current: LiveSession) -> list[dict[str, float]]:
        window = max(prediction_window_min, 0.0)
        if window <= 0:
            return []
        step = max(min(prediction_step_min, window), 0.1)
        forecast = current.copy(history_limit=0)
        points = [forecast.snapshot().as_dict()]
        elapsed = 0.0
        while elapsed < window:
            dt = min(step, window - elapsed)
            points.append(forecast.step(dt).as_dict())
            elapsed += dt
        return points

    async def emit_tick(
        snap_dict: dict[str, float],
        *,
        event: str = "tick",
        prediction: list[dict[str, float]] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"type": event, "snapshot": snap_dict}
        if prediction is not None:
            payload["prediction"] = prediction
            payload["prediction_window_min"] = prediction_window_min
        await send(payload)

    async def ticker() -> None:
        nonlocal playing
        try:
            while True:
                await asyncio.sleep(wall_tick_s)
                snap_dict: dict[str, float] | None = None
                prediction: list[dict[str, float]] | None = None
                async with session_lock:
                    if not playing or session is None:
                        continue
                    dt = sim_min_per_wall_s * wall_tick_s
                    snap = await asyncio.to_thread(session.step, dt)
                    snap_dict = snap.as_dict()
                    prediction = await asyncio.to_thread(prediction_for, session)
                if snap_dict is not None:
                    await emit_tick(snap_dict, prediction=prediction)
        except asyncio.CancelledError:
            return

    def ensure_ticker() -> None:
        nonlocal tick_task
        if tick_task is None or tick_task.done():
            tick_task = asyncio.create_task(ticker())

    try:
        await send({"type": "hello", "message": "teorell live"})
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send({"type": "error", "message": "invalid JSON"})
                continue

            mtype = msg.get("type")
            if mtype == "start":
                playing = False
                agent = AGENTS.get(str(msg.get("agent", "sevoflurane")).lower(), SEVOFLURANE)
                patient = _patient_from(msg)
                volatile_enabled = bool(msg.get("volatile_enabled", True))
                speed = float(msg.get("speed", LIVE_SIM_MIN_PER_WALL_S))
                if speed <= 0:
                    speed = LIVE_SIM_MIN_PER_WALL_S
                prediction_window_min = min(
                    max(float(msg.get("prediction_window_min", prediction_window_min)), 0.0),
                    60.0,
                )

                def _new_session() -> LiveSession:
                    s = LiveSession(patient=patient, volatile_agent=agent)
                    s.volatile_enabled = volatile_enabled
                    return s

                async with session_lock:
                    session = await asyncio.to_thread(_new_session)
                    snap = await asyncio.to_thread(session.snapshot)
                    prediction = await asyncio.to_thread(prediction_for, session)
                sim_min_per_wall_s = speed
                ensure_ticker()
                await send(
                    {
                        "type": "started",
                        "snapshot": snap.as_dict(),
                        "prediction": prediction,
                        "prediction_window_min": prediction_window_min,
                        "speed": sim_min_per_wall_s,
                    }
                )

            elif mtype == "play":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                playing = True
                ensure_ticker()
                await send({"type": "playing"})

            elif mtype == "pause":
                playing = False
                await send({"type": "paused"})

            elif mtype == "set_speed":
                sim_min_per_wall_s = max(
                    float(msg.get("speed", LIVE_SIM_MIN_PER_WALL_S)),
                    LIVE_SIM_MIN_PER_WALL_S,
                )
                await send({"type": "speed", "speed": sim_min_per_wall_s})

            elif mtype == "set_prediction_window":
                prediction_window_min = min(
                    max(float(msg.get("minutes", prediction_window_min)), 0.0),
                    60.0,
                )
                if session is None:
                    await send(
                        {
                            "type": "prediction_window",
                            "prediction_window_min": prediction_window_min,
                            "prediction": [],
                        }
                    )
                    continue
                async with session_lock:
                    snap = await asyncio.to_thread(session.snapshot)
                    prediction = await asyncio.to_thread(prediction_for, session)
                await send(
                    {
                        "type": "prediction_window",
                        "snapshot": snap.as_dict(),
                        "prediction": prediction,
                        "prediction_window_min": prediction_window_min,
                    }
                )

            elif mtype == "bolus":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                drug = str(msg.get("drug", "")).lower()
                amount = float(msg.get("amount", 0))
                async with session_lock:
                    if drug == "propofol":
                        snap = await asyncio.to_thread(session.bolus_propofol, amount)
                    elif drug == "remifentanil":
                        snap = await asyncio.to_thread(session.bolus_remifentanil, amount)
                    elif drug == "alfentanil":
                        snap = await asyncio.to_thread(session.bolus_alfentanil, amount)
                    else:
                        await send({"type": "error", "message": f"unknown drug {drug}"})
                        continue
                    prediction = await asyncio.to_thread(prediction_for, session)
                await emit_tick(snap.as_dict(), event="bolus", prediction=prediction)

            elif mtype == "set_infusion":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                drug = str(msg.get("drug", "")).lower()
                rate = float(msg.get("rate", 0))
                async with session_lock:
                    if drug == "propofol":
                        session.set_propofol_infusion(rate)
                    elif drug == "remifentanil":
                        session.set_remifentanil_infusion(rate)
                    elif drug == "alfentanil":
                        session.set_alfentanil_infusion(rate)
                    else:
                        await send({"type": "error", "message": f"unknown drug {drug}"})
                        continue
                    snap = await asyncio.to_thread(session.snapshot)
                    prediction = await asyncio.to_thread(prediction_for, session)
                await emit_tick(snap.as_dict(), event="infusion", prediction=prediction)

            elif mtype == "set_vaporizer":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                vol = float(msg.get("vol_pct", 0))
                fgf = msg.get("fgf")
                async with session_lock:
                    session.set_vaporizer(vol, float(fgf) if fgf is not None else None)
                    snap = await asyncio.to_thread(session.snapshot)
                    prediction = await asyncio.to_thread(prediction_for, session)
                await emit_tick(snap.as_dict(), event="vaporizer", prediction=prediction)

            elif mtype == "reset":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                playing = False
                async with session_lock:
                    snap = await asyncio.to_thread(session.reset)
                    prediction = await asyncio.to_thread(prediction_for, session)
                await emit_tick(snap.as_dict(), event="reset", prediction=prediction)

            elif mtype == "history":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                async with session_lock:
                    points = list(session.history[-500:])
                await send({"type": "history", "points": points})

            else:
                await send({"type": "error", "message": f"unknown type {mtype}"})

    except WebSocketDisconnect:
        pass
    finally:
        playing = False
        if tick_task is not None:
            tick_task.cancel()
            try:
                await tick_task
            except asyncio.CancelledError:
                pass
