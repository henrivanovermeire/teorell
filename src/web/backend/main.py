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
    # Teaching default: 1 wall-second → 1 sim-minute
    sim_min_per_wall_s = 1.0
    wall_tick_s = 0.1
    tick_task: asyncio.Task[None] | None = None
    # Serialize mutations: ticker to_thread vs bolus/reset on the same session.
    session_lock = asyncio.Lock()

    async def send(payload: dict[str, Any]) -> None:
        await ws.send_text(json.dumps(payload))

    async def emit_tick(snap_dict: dict[str, float], *, event: str = "tick") -> None:
        await send({"type": event, "snapshot": snap_dict})

    async def ticker() -> None:
        nonlocal playing
        try:
            while True:
                await asyncio.sleep(wall_tick_s)
                snap_dict: dict[str, float] | None = None
                async with session_lock:
                    if not playing or session is None:
                        continue
                    dt = sim_min_per_wall_s * wall_tick_s
                    snap = await asyncio.to_thread(session.step, dt)
                    snap_dict = snap.as_dict()
                if snap_dict is not None:
                    await emit_tick(snap_dict)
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
                speed = float(msg.get("speed", 1.0))
                if speed <= 0:
                    speed = 1.0

                def _new_session() -> LiveSession:
                    s = LiveSession(patient=patient, volatile_agent=agent)
                    s.volatile_enabled = volatile_enabled
                    return s

                async with session_lock:
                    session = await asyncio.to_thread(_new_session)
                    snap = await asyncio.to_thread(session.snapshot)
                sim_min_per_wall_s = speed
                ensure_ticker()
                await send(
                    {
                        "type": "started",
                        "snapshot": snap.as_dict(),
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
                sim_min_per_wall_s = max(float(msg.get("speed", 1.0)), 0.01)
                await send({"type": "speed", "speed": sim_min_per_wall_s})

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
                await emit_tick(snap.as_dict(), event="bolus")

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
                await emit_tick(snap.as_dict(), event="infusion")

            elif mtype == "set_vaporizer":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                vol = float(msg.get("vol_pct", 0))
                fgf = msg.get("fgf")
                async with session_lock:
                    session.set_vaporizer(vol, float(fgf) if fgf is not None else None)
                    snap = await asyncio.to_thread(session.snapshot)
                await emit_tick(snap.as_dict(), event="vaporizer")

            elif mtype == "reset":
                if session is None:
                    await send({"type": "error", "message": "start a session first"})
                    continue
                playing = False
                async with session_lock:
                    snap = await asyncio.to_thread(session.reset)
                await emit_tick(snap.as_dict(), event="reset")

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
