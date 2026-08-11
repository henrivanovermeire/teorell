# Roadmap

Educational PK/PD evolution for **teorell**: grow the dual-core simulator (IV + volatiles → predicted BIS) toward a BAS-class drug library without pretending to be a clinical decision-support system.

Priorities favour **teaching fidelity** (published models, clear units, testable equipotency) over breadth for its own sake.

## Where we are

| Layer | Today |
|-------|--------|
| IV PK | 3-compartment + effect site; Schnider propofol, Minto remifentanil, Scott alfentanil |
| Volatile PK | Gas Man–style circuit/alveoli/VRG/muscle/fat; λ/MAC for sevo, iso, des, halo |
| PD / BIS | Bouillon (TIVA) + Schumacher hypnotic U (propofol ± sevo-eq) + remi-eq opioids |
| Control | Manual bolus / infusion / vaporizer; live WebSocket UI |
| Not yet | Effect-site TCI, N₂O / second-gas, NMB or local-anesthetic PD, pediatric covariates |

Detailed references live in the README catalog tables.

---

## Phase 0 — Harden the dual core *(near-term)*

Make the existing surface trustworthy before adding many new agents.

- [ ] Document and test **MAC-scaled sevo-equivalents** for isoflurane / desflurane / halothane (already runnable; treat as first-class in examples + live UI defaults).
- [ ] Unify units and API naming (`amount_mg` vs µg opioids) so new models do not inherit footguns.
- [ ] Regression fixtures: fixed patient + regimen → golden Ce / FA / BIS traces for Schnider, Minto, Scott, sevoflurane Gas Man.
- [ ] Optional: Eleveld propofol and/or Marsh as alternate propofol parameterizations (same engine, different `parameters`).

**Exit:** Live UI + `simulate_anesthesia` feel solid for propofol ± remi/alfentanil ± modern volatiles.

---

## Phase 1 — Complete the volatile library

λ/MAC already exist for the four common agents; extend physicochemical coverage and PD honesty.

| Priority | Agent | Work |
|----------|--------|------|
| 1 | **Isoflurane / desflurane / halothane** | Agent-specific teaching examples; optional literature C50_BIS where published (else keep MAC→sevo scaling, labelled as such) |
| 2 | **Enflurane** | λ + MAC from Lowe / catalog; Gas Man only; MAC-scaled BIS |
| 3 | **N₂O** | Second-gas / concentration effect; circuit model extension (not a drop-in `VolatileAgent`) |
| 4 | **Xenon** | Partition coefficients (O'Brien & Veall); niche, low priority |
| 5 | **Ether** | Historical / teaching only (Poulin & Krishnan style λ) |

Also:

- [ ] Age-adjusted MAC (Mapleson / Nickalls–Mapleson) as an opt-in modifier on `VolatileAgent`.
- [ ] Vessel-poor group and/or metabolic loss hooks if Gas Man teaching scenarios need them.
- [ ] Live UI: agent picker already present — surface MAC fraction and sevo-eq clearly per agent.

**Exit:** Any catalogued halogenated agent runs end-to-end; N₂O either implemented or explicitly deferred with rationale.

---

## Phase 2 — Opioid spine (fentanyl family)

Closest educational gap vs BAS / OR practice after remi + alfentanil.

| Priority | Drug | Model target | Equipotency / PD notes |
|----------|------|--------------|-------------------------|
| 1 | **Fentanyl** | Shafer et al. | Map Ce → remi-eq (or fentanyl-centric surface); document plasma vs effect-site conventions |
| 2 | **Sufentanil** | Gepts et al. | Same remi-eq bridge as other µ-agonists |
| 3 | **Morphine** | Sarton et al. (or standard 3-CMT teaching set) | Active metabolite (M6G) — start parent-only, flag limitation |
| 4 | **Hydromorphone** | Hill & Zacny / clinical PK sets | Remi-eq or separate C50 when evidence allows |
| 5 | **Methadone / meperidine** | Inturrisi / Qiao & Fung | Lower priority; long ke0 / active metabolites |

Also:

- [ ] Central **opioid equipotency table** (literature ratios, citation per row) used by `CombinedBIS` / Bouillon arm.
- [ ] Live UI boluses/infusions for each new opioid with correct µg vs mg labelling.

**Exit:** Propofol + fentanyl ± volatile is a first-class teaching scenario.

---

## Phase 3 — Hypnotics & induction agents beyond propofol

| Priority | Drug | Model target | Notes |
|----------|------|--------------|--------|
| 1 | **Midazolam** | Greenblatt et al. | EEG/PD endpoints differ from BIS; may need separate PD or “sedation score” stub |
| 2 | **Thiopental** | Stanski & Maitre | Classic induction PK; BIS surface not 1:1 with propofol |
| 3 | **Diazepam / lorazepam** | Greenblatt | Teaching / ICU sedation context |
| 4 | **Fospropofol** | Fechner et al. | Prodrug → propofol; couple to existing propofol effect site |

**Exit:** At least one non-propofol IV hypnotic with published PK in the engine; PD either mapped carefully or exposed as Ce-only until a validated surface exists.

---

## Phase 4 — Neuromuscular blockers

Separate PD endpoint (TOF / twitch), not BIS.

| Priority | Drug | Model target |
|----------|------|--------------|
| 1 | **Rocuronium** | Plaud et al. |
| 2 | **Cisatracurium** | Tran et al. |
| 3 | **Vecuronium / pancuronium** | Rupp et al. |
| 4 | **Atracurium / succinylcholine / d-tubocurarine** | Catalog references |

Also:

- [ ] Parallel “NMB core”: Ce or biophase → predicted twitch height.
- [ ] Live UI strip for TOF alongside BIS (optional panel).
- [ ] Sugammadex antagonism — later, after rocuronium PK/PD is stable.

**Exit:** One aminosteroid + one benzylisoquinolinium with educational twitch curves.

---

## Phase 5 — Local anesthetics (IV / systemic teaching)

Systemic toxicity / plasma concentration teaching — not neuraxial spread.

| Priority | Drug | Model target |
|----------|------|--------------|
| 1 | **Lidocaine** | Rowland et al. |
| 2 | **Bupivacaine / ropivacaine / mepivacaine / etidocaine** | Tucker & Mather / Lee et al. |

Also:

- [ ] Explicit warnings: IV LA models are for concentration education, not dosing advice.
- [ ] Optional coupling to CNS/cardiac toxicity thresholds as **illustrative** overlays only.

---

## Cross-cutting capabilities

These unlock many drugs without per-agent UI rewrites.

| Capability | Why |
|------------|-----|
| **Effect-site / plasma TCI** | Target Ce or Cp → computed infusion; needed for realistic fentanyl/propofol teaching |
| **Pediatric / obese covariates** | Eleveld-style or published pediatric sets; gate behind clear labels |
| **Multi-agent interaction surfaces** | Beyond β=0 Greco; optional Heyse-style synergy flags |
| **Scenario / regimen presets** | BAS-like induction–maintenance–emergence scripts |
| **Export** | CSV / JSON traces for classroom use |
| **Model registry** | `DrugSpec` metadata: units, PMID, default ke0, PD endpoint — drives API + UI |

---

## Suggested sequencing (summary)

```text
Phase 0  Harden dual core + tests + units
   ↓
Phase 1  Volatiles complete (λ/MAC + honest BIS scaling; N₂O optional)
   ↓
Phase 2  Fentanyl / sufentanil (+ equipotency table)
   ↓
Phase 3  Midazolam / thiopental (hypnotics)
   ↓
Phase 4  Rocuronium / cisatracurium (NMB core)
   ↓
Phase 5  Lidocaine ± other IV LAs
```

TCI and the model registry can start as soon as Phase 2 begins; they should not block Phase 1.

---

## Non-goals (for now)

- Real-time EEG processing or monitor-faithful BIS.
- Closed-loop clinical controllers or dose recommendations.
- Full PBPK replacing the mammillary + Gas Man teaching cores.
- Claiming regulatory or clinical validation.

---

## How to extend one drug (checklist)

1. Add parameter factory under `src/teorell_core/models/` (or `volatile/properties.py` for gases).
2. Wire into `simulate_tiva` / `simulate_anesthesia` / `LiveSession` with **explicit units**.
3. Cite PMID in README catalog; mark the row bold when coded.
4. Add pytest golden-path + one `examples/*.py` plot.
5. Expose controls in `apps/api` + `apps/web` only after core tests pass.
6. Update this roadmap checkboxes when a phase item ships.

References and the full planned catalog remain in [README.md](README.md).
