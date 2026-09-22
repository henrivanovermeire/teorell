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

const PREDICTION_WINDOW_MIN = 60;
const LIVE_SIM_MIN_PER_WALL_S = 1 / 60;
/** Chart redraw rate; metric tiles still update every WS tick. */
const CHART_HZ = 4;
const CHART_MIN_MS = 1000 / CHART_HZ;

const tooltipStyle = {
  background: "#1a222c",
  border: "1px solid #2c3848",
} as const;

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

type Phase = "landing" | "sim";

export default function App() {
  const client = useRef<LiveClient | null>(null);
  const lastChartAt = useRef(0);
  const latestSnap = useRef<Snapshot>(emptySnap);
  const pendingEnterSim = useRef(false);

  const [phase, setPhase] = useState<Phase>("landing");
  const [connected, setConnected] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [showConcentrations, setShowConcentrations] = useState(true);
  const [snap, setSnap] = useState<Snapshot>(emptySnap);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [prediction, setPrediction] = useState<Snapshot[]>([]);
  const [speed, setSpeed] = useState(LIVE_SIM_MIN_PER_WALL_S);
  const [predictionWindow, setPredictionWindow] = useState(PREDICTION_WINDOW_MIN);
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

  const appendChart = useCallback((s: Snapshot) => {
    lastChartAt.current = performance.now();
    setHistory((h) => {
      const next = [...h, s].filter(
        (point) => point.t_min <= PREDICTION_WINDOW_MIN,
      );
      return next;
    });
  }, []);

  const onSnapshot = useCallback(
    (s: Snapshot, forceChart = false, nextPrediction?: Snapshot[]) => {
      latestSnap.current = s;
      setSnap(s);
      if (nextPrediction) setPrediction(nextPrediction);
      const now = performance.now();
      if (forceChart || now - lastChartAt.current >= CHART_MIN_MS) {
        appendChart(s);
      }
    },
    [appendChart],
  );

  useEffect(() => {
    const c = connectLive(
      (msg) => {
        if (msg.type === "hello") {
          setStatus("connected");
        }
        if (msg.type === "started") {
          lastChartAt.current = 0;
          latestSnap.current = msg.snapshot;
          setHistory([msg.snapshot]);
          setPrediction(msg.prediction ?? []);
          setSnap(msg.snapshot);
          setSpeed(msg.speed);
          if (msg.prediction_window_min !== undefined) {
            setPredictionWindow(msg.prediction_window_min);
          }
          setStatus("ready");
          if (pendingEnterSim.current) {
            pendingEnterSim.current = false;
            setPhase("sim");
            c.send({ type: "play" });
          }
        }
        if (msg.type === "playing") {
          setPlaying(true);
          setStatus("playing");
        }
        if (msg.type === "paused") {
          setPlaying(false);
          setStatus("paused");
          appendChart(latestSnap.current);
        }
        if (msg.type === "speed") setSpeed(msg.speed);
        if (msg.type === "prediction_window") {
          setPredictionWindow(msg.prediction_window_min);
          setPrediction(msg.prediction);
          if (msg.snapshot) onSnapshot(msg.snapshot, true, msg.prediction);
        }
        if (msg.type === "tick") {
          onSnapshot(msg.snapshot, false, msg.prediction);
          if (msg.prediction_window_min !== undefined) {
            setPredictionWindow(msg.prediction_window_min);
          }
        }
        if (
          msg.type === "bolus" ||
          msg.type === "infusion" ||
          msg.type === "vaporizer" ||
          msg.type === "reset"
        ) {
          onSnapshot(msg.snapshot, true, msg.prediction);
          if (msg.prediction_window_min !== undefined) {
            setPredictionWindow(msg.prediction_window_min);
          }
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
  }, [onSnapshot, appendChart]);

  const send = useCallback((msg: Record<string, unknown>) => {
    client.current?.send(msg);
  }, []);

  const startSimulation = useCallback(() => {
    if (!connected) return;
    pendingEnterSim.current = true;
    send({
      type: "start",
      age,
      weight,
      height,
      sex,
      agent,
      speed,
      volatile_enabled: true,
      prediction_window_min: predictionWindow,
    });
  }, [connected, send, age, weight, height, sex, agent, speed, predictionWindow]);

  const backToLanding = useCallback(() => {
    send({ type: "pause" });
    setPlaying(false);
    setPhase("landing");
    setHistory([]);
    setPrediction([]);
    setSnap(emptySnap);
    latestSnap.current = emptySnap;
    setStatus(connected ? "connected" : "disconnected");
  }, [send, connected]);

  const chartData = useMemo(() => {
    const rows = new Map<number, Record<string, number>>();
    const rowFor = (t: number) => {
      const key = Number(t.toFixed(2));
      const existing = rows.get(key);
      if (existing) return existing;
      const row: Record<string, number> = { t: key };
      rows.set(key, row);
      return row;
    };

    for (const h of history) {
      if (h.t_min > PREDICTION_WINDOW_MIN) continue;
      const row = rowFor(h.t_min);
      row.BIS = h.bis;
      row["Prop Ce"] = h.propofol_ce;
      row["Remi Ce"] = h.remifentanil_ce;
      row.VRG = h.vrg;
      row.FA = h.fa;
    }

    for (const h of prediction) {
      if (h.t_min < snap.t_min || h.t_min > PREDICTION_WINDOW_MIN) continue;
      const row = rowFor(h.t_min);
      row["BIS forecast"] = h.bis;
      row["Prop Ce forecast"] = h.propofol_ce;
      row["Remi Ce forecast"] = h.remifentanil_ce;
      row["VRG forecast"] = h.vrg;
      row["FA forecast"] = h.fa;
    }

    return [...rows.values()].sort((a, b) => a.t - b.t);
  }, [history, prediction, snap.t_min]);

  const agentLabel =
    agent.charAt(0).toUpperCase() + agent.slice(1);

  if (phase === "landing") {
    return (
      <div className="landing">
        <div className="landing-card">
          <p className="landing-brand">teorell</p>
          <h1>Patient</h1>
          <p className="landing-lead">
            Review demographics and volatile agent, then start the live
            simulation. Educational only — not a medical device.
          </p>
          <p className={`status ${connected ? "on" : ""}`}>
            {connected ? "Ready" : "Connecting…"}
          </p>

          <div className="field">
            <label>Age (y)</label>
            <input
              type="number"
              min={18}
              max={90}
              value={age}
              onChange={(e) => setAge(Number(e.target.value))}
            />
          </div>
          <div className="row">
            <div className="field">
              <label>Weight (kg)</label>
              <input
                type="number"
                min={40}
                max={150}
                value={weight}
                onChange={(e) => setWeight(Number(e.target.value))}
              />
            </div>
            <div className="field">
              <label>Height (cm)</label>
              <input
                type="number"
                min={140}
                max={210}
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
            <label>Volatile agent</label>
            <select value={agent} onChange={(e) => setAgent(e.target.value)}>
              <option value="sevoflurane">Sevoflurane</option>
              <option value="isoflurane">Isoflurane</option>
              <option value="desflurane">Desflurane</option>
              <option value="halothane">Halothane</option>
            </select>
          </div>
          <div className="field">
            <label>Playback</label>
            <input type="text" value="Live / real time" disabled />
          </div>
          <div className="field">
            <label>Prediction window</label>
            <input type="text" value="60 min" disabled />
          </div>

          <button
            className="primary landing-cta"
            disabled={!connected}
            onClick={startSimulation}
          >
            Start simulation
          </button>
          <p className="disclaimer">
            Schnider · Minto · Scott · Gas Man · Bouillon/Schumacher BIS
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>teorell live</h1>
        <p className={`status ${connected ? "on" : ""}`}>{status}</p>

        <div className="patient-locked">
          <h2>Patient</h2>
          <dl>
            <div>
              <dt>Age</dt>
              <dd>{age} y</dd>
            </div>
            <div>
              <dt>Weight</dt>
              <dd>{weight} kg</dd>
            </div>
            <div>
              <dt>Height</dt>
              <dd>{height} cm</dd>
            </div>
            <div>
              <dt>Sex</dt>
              <dd>{sex === "male" ? "Male" : "Female"}</dd>
            </div>
            <div>
              <dt>Volatile</dt>
              <dd>{agentLabel}</dd>
            </div>
          </dl>
        </div>

        <div className="field">
          <label>Playback</label>
          <input type="text" value="Live / real time" disabled />
        </div>

        <div className="field">
          <label>Prediction window</label>
          <input type="text" value="60 min" disabled />
        </div>

        <div className="row">
          <button onClick={() => send({ type: "play" })}>Play</button>
          <button onClick={() => send({ type: "pause" })}>Pause</button>
          <button className="danger" onClick={() => send({ type: "reset" })}>
            Reset
          </button>
        </div>
        <button type="button" onClick={backToLanding}>
          New patient
        </button>
        <p className="disclaimer">
          Demographics locked for this case. Use New patient to change them.
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
          <div className="chart-head">
            <h2>BIS: actual chasing 60 min forecast</h2>
            <button
              type="button"
              className={`toggle ${showConcentrations ? "on" : ""}`}
              onClick={() => setShowConcentrations((v) => !v)}
            >
              {showConcentrations ? "Hide concentrations" : "Show concentrations"}
            </button>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#2c3848" strokeDasharray="3 3" />
              <XAxis
                dataKey="t"
                type="number"
                domain={[0, PREDICTION_WINDOW_MIN]}
                stroke="#8b9bb0"
                tick={{ fontSize: 11 }}
              />
              <YAxis domain={[0, 100]} stroke="#8b9bb0" tick={{ fontSize: 11 }} />
              {!playing && <Tooltip contentStyle={tooltipStyle} />}
              <Line
                type="monotone"
                dataKey="BIS"
                stroke="#3ecf8e"
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="BIS forecast"
                stroke="#3ecf8e"
                strokeDasharray="5 5"
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {showConcentrations && (
          <div className="chart-panel">
            <h2>Concentrations / tensions</h2>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="#2c3848" strokeDasharray="3 3" />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={[0, PREDICTION_WINDOW_MIN]}
                  stroke="#8b9bb0"
                  tick={{ fontSize: 11 }}
                />
                <YAxis stroke="#8b9bb0" tick={{ fontSize: 11 }} />
                {!playing && <Tooltip contentStyle={tooltipStyle} />}
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Prop Ce"
                  stroke="#3d9cf0"
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="Prop Ce forecast"
                  stroke="#3d9cf0"
                  strokeDasharray="5 5"
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="Remi Ce"
                  stroke="#c084fc"
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="Remi Ce forecast"
                  stroke="#c084fc"
                  strokeDasharray="5 5"
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="VRG"
                  stroke="#f0b429"
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="VRG forecast"
                  stroke="#f0b429"
                  strokeDasharray="5 5"
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="FA"
                  stroke="#f97316"
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="FA forecast"
                  stroke="#f97316"
                  strokeDasharray="5 5"
                  dot={false}
                  strokeWidth={1.25}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </main>
    </div>
  );
}
