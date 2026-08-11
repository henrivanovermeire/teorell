# Architecture

teorell separates a **pure simulation library** from an optional **live teaching stack**. The library is what ships on PyPI as `teorell-core`; the UI is application code in this repository.

## High-level diagram

```text
┌─────────────────────────────────────────────────────────────┐
│  Browser (Vite React)                                       │
│  landing → LiveSession controls → charts (throttled)        │
└────────────────────────────┬────────────────────────────────┘
                             │ WebSocket JSON  /ws
┌────────────────────────────▼────────────────────────────────┐
│  web.backend (FastAPI)                                      │
│  one LiveSession per connection · asyncio.to_thread(step)   │
└────────────────────────────┬────────────────────────────────┘
                             │ imports
┌────────────────────────────▼────────────────────────────────┐
│  teorell_core                                               │
│  IV PK · volatile Gas Man · BIS PD · LiveSession            │
└─────────────────────────────────────────────────────────────┘
```

Docker Compose wraps the same idea: **backend** image = Python + `teorell_core` + FastAPI; **frontend** image = static Vite build behind nginx that proxies `/ws` and `/health`.

## Repository layout

```text
src/
  teorell_core/     # PyPI package (library)
  web/
    backend/        # FastAPI WebSocket server
    frontend/       # React UI
docker/             # Dockerfiles + nginx.conf
docs/wiki/          # Canonical GitHub Wiki sources (this tree)
examples/           # Scripted scenarios
tests/              # pytest
```

The wheel built from `pyproject.toml` includes **only** `teorell_core` (numpy dependency). It does not ship `src/web/`.

## Simulation core (`teorell_core`)

### IV arm

- 3-compartment mammillary model + effect site
- Time integration via **matrix exponential** between grid points (`simulator.py`)
- Adult covariate models:
  - Propofol — Schnider
  - Remifentanil — Minto
  - Alfentanil — Scott & Stanski (weight-scaled)

### Volatile arm

- Gas Man–style circuit / alveoli / VRG / muscle / fat (`volatile/gasman.py`)
- λ and MAC tables for sevoflurane, isoflurane, desflurane, halothane
- Schumacher BIS C50 is measured for sevoflurane; other agents use **MAC-scaled sevoflurane equivalents** when no agent-specific C50 is set

### Pharmacodynamics (predicted BIS)

Not EEG processing — a **modelled** processed-EEG index for teaching.

**TIVA-only** (`simulate_tiva`):

1. Effect-site concentrations for propofol ± opioids  
2. `remi_eq = Ce_remi + Ce_alfentanil / 40` (Egan 1999 whole-blood ratio)  
3. Bouillon surface (C50p ≈ 4.47 µg/mL, C50r ≈ 19.3 ng/mL)

**Dual-core** (`simulate_anesthesia` / live):

1. Volatile PK → VRG tension  
2. Hypnotic U (Schumacher): `U_h = Ce_prop / 3.68 + sevo_eq / 1.53`  
3. Opioid arm as remi-eq / 19.3; combine with Bouillon-style Hill (β = 0 → additive U)  
4. `BIS = 97.4 − 97.4 · U^γ / (1 + U^γ)` with γ ≈ 1.43  

Caveat: Bouillon’s TIVA-only C50p differs from Schumacher’s C50p when volatiles are present — intentional dual-path behaviour, documented in the README.

### Live stepper

`LiveSession` keeps mutable IV and volatile state, supports `step(dt)`, boluses, infusions, and vaporizer changes, and records a rolling history. Batch APIs (`simulate_tiva`, `simulate_anesthesia`) remain available for offline / example scripts.

## Live web stack

### Backend (`src/web/backend`)

- FastAPI app: `GET /health`, `WS /ws`
- Protocol (JSON messages): `start`, `play`, `pause`, `set_speed`, `bolus`, `set_infusion`, `set_vaporizer`, `reset`, `history`
- **Session isolation:** each WebSocket connection owns its own `LiveSession` (locals on the handler). Connections share one process/CPU, not sim state.
- PK work runs in **`asyncio.to_thread`** with a per-connection lock so the event loop stays responsive under multi-tab play.

### Frontend (`src/web/frontend`)

- Landing page: editable patient / agent / speed → **Start simulation**
- Sim pane: demographics **read-only**; play is default after start
- Metrics update every tick; Recharts history throttled (~4 Hz); tooltips only when paused

Dev proxy: Vite forwards `/ws` → `127.0.0.1:8000`. Production Docker: nginx terminates HTTP and upgrades WebSockets to the backend service.

## Scaling notes

Suitable for classroom / demo concurrency (tens of sessions) with chart throttling. Horizontal scale later needs sticky load balancing or an external session store — not required for the educational MVP. See project discussions / ROADMAP for Docker and drug expansion.

## Related wiki pages

- [[Getting-Started]] — install and run  
- [[Home]] — overview
