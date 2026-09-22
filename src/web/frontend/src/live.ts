export type Snapshot = {
  t_min: number;
  bis: number;
  propofol_cp: number;
  propofol_ce: number;
  remifentanil_ce: number;
  alfentanil_ce: number;
  opioid_remi_eq: number;
  fi: number;
  fa: number;
  vrg: number;
  mac: number;
  propofol_infusion: number;
  remifentanil_infusion: number;
  alfentanil_infusion: number;
  vaporizer: number;
  fgf: number;
};

export type ServerMessage =
  | { type: "hello"; message: string }
  | {
      type: "started";
      snapshot: Snapshot;
      prediction?: Snapshot[];
      prediction_window_min?: number;
      speed: number;
    }
  | { type: "playing" }
  | { type: "paused" }
  | { type: "speed"; speed: number }
  | {
      type: "prediction_window";
      snapshot?: Snapshot;
      prediction: Snapshot[];
      prediction_window_min: number;
    }
  | {
      type: "tick" | "bolus" | "infusion" | "vaporizer" | "reset";
      snapshot: Snapshot;
      prediction?: Snapshot[];
      prediction_window_min?: number;
    }
  | { type: "history"; points: Snapshot[] }
  | { type: "error"; message: string };

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  // Dev: Vite proxies /ws → backend. Explicit override via VITE_WS_URL.
  const env = import.meta.env.VITE_WS_URL as string | undefined;
  if (env) return env;
  return `${proto}://${window.location.host}/ws`;
}

export type LiveClient = {
  send: (msg: Record<string, unknown>) => void;
  close: () => void;
};

export function connectLive(
  onMessage: (msg: ServerMessage) => void,
  onStatus: (connected: boolean) => void,
): LiveClient {
  const ws = new WebSocket(wsUrl());
  ws.onopen = () => onStatus(true);
  ws.onclose = () => onStatus(false);
  ws.onerror = () => onStatus(false);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data as string) as ServerMessage);
    } catch {
      /* ignore */
    }
  };
  return {
    send: (msg) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    },
    close: () => ws.close(),
  };
}
