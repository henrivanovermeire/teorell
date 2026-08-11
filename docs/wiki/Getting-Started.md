![teorell](https://raw.githubusercontent.com/henrivanovermeire/teorell/main/assets/teorell.png)

# Getting Started

teorell has two surfaces:

1. **`teorell-core`** — Python PK/PD library (what you get from PyPI)
2. **Live teaching UI** — FastAPI WebSocket + Vite React (this GitHub repo only)

Educational use only — not for clinical care.

## Install the core (PyPI)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install teorell-core
```

Minimal simulation:

```python
from teorell_core import (
    Bolus,
    Infusion,
    Patient,
    Regimen,
    SEVOFLURANE,
    Sex,
    VolatileSchedule,
    simulate_anesthesia,
    simulate_tiva,
)

patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)

tiva = simulate_tiva(
    patient,
    propofol=Regimen(boluses=(Bolus(0.0, 100.0),), infusions=(Infusion(1.0, 29.0, 6.0),)),
    remifentanil=Regimen(infusions=(Infusion(1.0, 29.0, 0.2),)),
    duration_min=30.0,
)

anes = simulate_anesthesia(
    patient,
    propofol=Regimen(boluses=(Bolus(0.0, 80.0),)),
    volatile_agent=SEVOFLURANE,
    volatile_schedule=VolatileSchedule(segments=((0.0, 3.0, 6.0), (10.0, 1.5, 2.0))),
    duration_min=30.0,
)
print(anes.bis.min(), anes.mac_fraction.max(), anes.vrg_vol_pct[-1])
```

### Units (important)

| Drug | Dose / rate fields | Concentrations |
|------|--------------------|----------------|
| Propofol | mg, mg/min | µg/mL |
| Remifentanil / alfentanil | **µg**, µg/min | ng/mL |
| Volatiles | vaporizer vol%, FGF L/min | FI / FA / VRG vol%; MAC fraction |

Shared field names `amount_mg` / `rate_mg_per_min` still apply; for opioids pass **micrograms**.

## Develop from source (library + tests)

```bash
git clone https://github.com/henrivanovermeire/teorell.git
cd teorell
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Live UI (local)

Requires **Node.js / npm** and the `[live]` extras:

```bash
pip install -e ".[live]"
./scripts/run-live.sh
```

Open http://localhost:5173 → edit patient on the landing page → **Start simulation** (play starts automatically). Demographics are locked during the case; use **New patient** to return to the landing page.

Override ports: `API_PORT=8001 WEB_PORT=5174 ./scripts/run-live.sh`.

Manual two-terminal setup:

```bash
# terminal 1
PYTHONPATH=src uvicorn web.backend.main:app --reload --port 8000

# terminal 2
cd src/web/frontend && npm install && npm run dev
```

## Docker Compose

One command for the full stack (core inside the backend image + nginx UI with `/ws` proxy):

```bash
docker compose up --build
```

- UI: http://localhost:8080  
- API health: http://localhost:8000/health  

## Examples

From a source checkout (plots write PNGs under `examples/`, gitignored):

```bash
python examples/schnider_bolus.py
python examples/tiva_propofol_remifentanil_bis.py
python examples/sevoflurane_gasman_bis.py
```

## Next

- [[Architecture]] — how the dual core and live stack fit together  
- [Roadmap](https://github.com/henrivanovermeire/teorell/blob/main/ROADMAP.md) — planned drugs and volatiles
