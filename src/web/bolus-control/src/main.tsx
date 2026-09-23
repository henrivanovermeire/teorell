import React, { type ChangeEvent, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  const [amount, setAmount] = useState(50);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("Ready");

  async function administerBolus() {
    setBusy(true);
    setStatus(`Giving ${amount} mg propofol…`);
    try {
      const res = await fetch("/bolus/propofol", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount_mg: amount }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof body.detail === "string" ? body.detail : res.statusText;
        throw new Error(detail);
      }
      const bis = body.snapshot?.bis;
      const time = body.snapshot?.t_min;
      setStatus(
        `Delivered ${amount} mg` +
          (typeof time === "number" ? ` at ${time.toFixed(1)} min` : "") +
          (typeof bis === "number" ? ` · BIS ${bis.toFixed(1)}` : ""),
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Bolus failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="control">
      <section className="card">
        <p className="brand">teorell</p>
        <h1>Propofol bolus</h1>
        <p className="hint">Mobile demo control. Open the main simulation first.</p>

        <label className="field">
          <span>Dose (mg)</span>
          <input
            type="number"
            min={1}
            max={500}
            step={5}
            value={amount}
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              setAmount(Number(event.target.value))
            }
          />
        </label>

        <div className="quick">
          {[20, 50, 100].map((dose) => (
            <button
              key={dose}
              type="button"
              className={amount === dose ? "selected" : ""}
              onClick={() => setAmount(dose)}
              disabled={busy}
            >
              {dose} mg
            </button>
          ))}
        </div>

        <button
          type="button"
          className="bolus"
          onClick={administerBolus}
          disabled={busy || amount <= 0}
        >
          {busy ? "Delivering…" : `Give ${amount} mg`}
        </button>

        <p className={`status ${status.startsWith("Delivered") ? "ok" : ""}`}>
          {status}
        </p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
