import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { connectLive, type LiveClient, type Snapshot } from "./live";

const MAX_POINTS = 600;

const emptySnap: Snapshot = {
  t_min: 0,
  bis: 97.4,
  propofol_cp: 0,
  propofol_ce: 0,
  remifentanil_ce: 0,
  alfentanil_ce: 0,
  opioid_remi_eq: 0,
  fi: 0,
  fa: 0,
  vrg: 0,
  mac: 0,
  propofol_infusion: 0,
  remifentanil_infusion: 0,
  alfentanil_infusion: 0,
  vaporizer: 0,
  fgf: 6,
};

export default function App() {
  const client = useRef<LiveClient | null>(null);
  const [connected, setConnected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [snap, setSnap] = useState<Snapshot>(emptySnap);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [speed, setSpeed] = useState(1);
  const [age, setAge] = useState(40);
  const [weight, setWeight] = useState(70);
  const [height, setHeight] = useState(170);
  const [sex, setSex] = useState<"male" | "female">("male");
  const [agent, setAgent] = useState("sevoflurane");
  const [propRate, setPropRate] = useState(0);
  const [remiRate, setRemiRate] = useState(0);
  const [vap, setVap] = useState(0);
  const [fgf, setFgf] = useState(6);
  const [status, setStatus] = useState("disconnected");

  const pushSnap = useCallback((s: Snapshot) => {
    setSnap(s);
    setHistory((h) => {
      const next = [...h, s];
      return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
    });
  }, []);

  useEffect(() => {
    const c = connectLive(
      (msg) => {
        if (msg.type === "hello") setStatus("connected");
        if (msg.type === "started") {
          setPlaying(false);
          setHistory([msg.snapshot]);
          setSnap(msg.snapshot);
          setSpeed(msg.speed);
          setStatus("ready");
        }
        if (msg.type === "playing") {
          setPlaying(true);
          setStatus("playing");
        }
        if (msg.type === "paused") {
          setPlaying(false);
          setStatus("paused");
        }
        if (msg.type === "speed") setSpeed(msg.speed);
        if (
          msg.type === "tick" ||
          msg.type === "bolus" ||
          msg.type === "infusion" ||
          msg.type === "vaporizer" ||
          msg.type === "reset"
        ) {
          pushSnap(msg.snapshot);
        }
        if (msg.type === "error") setStatus(msg.message);
      },
      (ok) => {
        setConnected(ok);
        setStatus(ok ? "connected" : "disconnected");
      },
    );
    client.current = c;
    return () => c.close();
  }, [pushSnap]);

  const send = useCallback((msg: Record<string, unknown>) => {
    client.current?.send(msg);
  }, []);

  const chartData = useMemo(
    () =>
      history.map((h) => ({
        t: Number(h.t_min.toFixed(2)),
        BIS: h.bis,
        "Prop Ce": h.propofol_ce,
        "Remi Ce": h.remifentanil_ce,
        VRG: h.vrg,
        FA: h.fa,
      })),
    [history],
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>teorell live</h1>
        <p>
          Real-time PK/PD over WebSocket. Educational only — not a medical
          device.
        </p>
        <p className={`status ${connected ? "on" : ""}`}>{status}</p>

        <div className="field">
          <label>Age</label>
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(Number(e.target.value))}
          />
        </div>
        <div className="row">
          <div className="field">
            <label>Weight kg</label>
            <input
              type="number"
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label>Height cm</label>
            <input
              type="number"
              value={height}
              onChange={(e) => setHeight(Number(e.target.value))}
            />
          </div>
        </div>
        <div className="field">
          <label>Sex</label>
          <select
            value={sex}
            onChange={(e) => setSex(e.target.value as "male" | "female")}
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
        <div className="field">
          <label>Volatile</label>
          <select value={agent} onChange={(e) => setAgent(e.target.value)}>
            <option value="sevoflurane">Sevoflurane</option>
            <option value="isoflurane">Isoflurane</option>
            <option value="desflurane">Desflurane</option>
            <option value="halothane">Halothane</option>
          </select>
        </div>
        <div className="field">
          <label>Speed (sim min / wall s)</label>
          <input
            type="number"
            min={0.1}
            step={0.1}
            value={speed}
            onChange={(e) => {
              const v = Number(e.target.value);
              setSpeed(v);
              send({ type: "set_speed", speed: v });
            }}
          />
        </div>

        <button
          className="primary"
          onClick={() =>
            send({
              type: "start",
              age,
              weight,
              height,
              sex,
              agent,
              speed,
              volatile_enabled: true,
            })
          }
        >
          Start session
        </button>
        <div className="row">
          <button onClick={() => send({ type: "play" })}>Play</button>
          <button onClick={() => send({ type: "pause" })}>Pause</button>
          <button className="danger" onClick={() => send({ type: "reset" })}>
            Reset
          </button>
        </div>
        <p className="disclaimer">
          Schnider · Minto · Scott · Gas Man · Bouillon/Schumacher BIS
        </p>
      </aside>

      <main className="main">
        <div className="metrics">
          <div className="metric">
            <div className="label">Time</div>
            <div className="value">{snap.t_min.toFixed(1)} min</div>
          </div>
          <div className="metric">
            <div className="label">BIS</div>
            <div className="value">{snap.bis.toFixed(1)}</div>
          </div>
          <div className="metric">
            <div className="label">Prop Ce</div>
            <div className="value">{snap.propofol_ce.toFixed(2)}</div>
          </div>
          <div className="metric">
            <div className="label">MAC</div>
            <div className="value">{snap.mac.toFixed(2)}</div>
          </div>
        </div>

        <div className="actions">
          <div className="group">
            <span>Propofol bolus (mg)</span>
            <div className="btns">
              {[20, 50, 100].map((mg) => (
                <button
                  key={mg}
                  onClick={() =>
                    send({ type: "bolus", drug: "propofol", amount: mg })
                  }
                >
                  {mg} mg
                </button>
              ))}
            </div>
          </div>
          <div className="group">
            <span>Remifentanil bolus (µg)</span>
            <div className="btns">
              {[25, 50, 100].map((ug) => (
                <button
                  key={ug}
                  onClick={() =>
                    send({ type: "bolus", drug: "remifentanil", amount: ug })
                  }
                >
                  {ug} µg
                </button>
              ))}
            </div>
          </div>
          <div className="group">
            <span>Propofol infusion mg/min</span>
            <div className="btns">
              <input
                type="number"
                min={0}
                step={0.5}
                value={propRate}
                onChange={(e) => setPropRate(Number(e.target.value))}
                style={{ width: 70 }}
              />
              <button
                onClick={() =>
                  send({
                    type: "set_infusion",
                    drug: "propofol",
                    rate: propRate,
                  })
                }
              >
                Set
              </button>
            </div>
          </div>
          <div className="group">
            <span>Remi infusion µg/min</span>
            <div className="btns">
              <input
                type="number"
                min={0}
                step={0.05}
                value={remiRate}
                onChange={(e) => setRemiRate(Number(e.target.value))}
                style={{ width: 70 }}
              />
              <button
                onClick={() =>
                  send({
                    type: "set_infusion",
                    drug: "remifentanil",
                    rate: remiRate,
                  })
                }
              >
                Set
              </button>
            </div>
          </div>
          <div className="group">
            <span>Vaporizer % / FGF</span>
            <div className="btns">
              <input
                type="number"
                min={0}
                step={0.1}
                value={vap}
                onChange={(e) => setVap(Number(e.target.value))}
                style={{ width: 60 }}
              />
              <input
                type="number"
                min={0.2}
                step={0.2}
                value={fgf}
                onChange={(e) => setFgf(Number(e.target.value))}
                style={{ width: 60 }}
              />
              <button
                onClick={() =>
                  send({ type: "set_vaporizer", vol_pct: vap, fgf })
                }
              >
                Set
              </button>
            </div>
          </div>
          <div className="group">
            <span>State</span>
            <div className="btns">
              <span style={{ color: playing ? "#3ecf8e" : "#8b9bb0" }}>
                {playing ? "▶ playing" : "⏸ paused"}
              </span>
            </div>
          </div>
        </div>

        <div className="chart-panel">
          <h2>Predicted BIS</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#2c3848" strokeDasharray="3 3" />
              <XAxis dataKey="t" stroke="#8b9bb0" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} stroke="#8b9bb0" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#1a222c",
                  border: "1px solid #2c3848",
                }}
              />
              <Line
                type="monotone"
                dataKey="BIS"
                stroke="#3ecf8e"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-panel">
          <h2>Concentrations / tensions</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#2c3848" strokeDasharray="3 3" />
              <XAxis dataKey="t" stroke="#8b9bb0" tick={{ fontSize: 11 }} />
              <YAxis stroke="#8b9bb0" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#1a222c",
                  border: "1px solid #2c3848",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="Prop Ce"
                stroke="#3d9cf0"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="Remi Ce"
                stroke="#c084fc"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="VRG"
                stroke="#f0b429"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="FA"
                stroke="#f97316"
                dot={false}
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  );
}
