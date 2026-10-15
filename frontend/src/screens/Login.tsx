import { useState } from "react";
import { ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import { BeaconMark } from "../components/icons";

const DEMO_EMAIL = "demo@faro.app";
const DEMO_PASSWORD = "FaroDemo2026!";

export function Login() {
  const { s, lang, setLang } = useI18n();
  const { signIn, register } = useAuth();
  const [mode, setMode] = useState<"in" | "up">("in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 0) setError(s.common.networkError);
        else if (e.status === 429) setError(s.auth.tooMany);
        else if (e.status === 401) setError(s.auth.badCreds);
        else setError(s.common.genericError);
      } else {
        setError(s.common.genericError);
      }
    } finally {
      setBusy(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(() =>
      mode === "in" ? signIn(email, password) : register(email, password, lang),
    );
  }

  return (
    <div className="app">
      <main className="main">
        <div className="wrap auth">
          <div className="beacon-panel" style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <BeaconMark size={34} />
              <h1 className="mt0" style={{ marginBottom: 0 }}>
                Faro
              </h1>
            </div>
            <p style={{ marginBottom: 0, marginTop: 10 }}>{s.auth.subtitle}</p>
          </div>

          <form className="card" onSubmit={submit}>
            <h2 className="mt0">{s.auth.welcome}</h2>

            {error && (
              <div className="flash flash--error" role="alert">
                {error}
              </div>
            )}

            <label className="field">
              <span>{s.auth.email}</span>
              <input
                className="input"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>

            <label className="field">
              <span>{s.auth.password}</span>
              <input
                className="input"
                type="password"
                autoComplete={mode === "in" ? "current-password" : "new-password"}
                required
                minLength={mode === "up" ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {mode === "up" && <span className="hint">{s.auth.passwordHint}</span>}
            </label>

            <button className="btn btn--big" type="submit" disabled={busy}>
              {mode === "in" ? s.auth.enter : s.auth.create}
            </button>

            <div className="btn-row" style={{ marginTop: 16, justifyContent: "space-between" }}>
              <button
                type="button"
                className="btn btn--quiet"
                onClick={() => setMode(mode === "in" ? "up" : "in")}
              >
                {mode === "in" ? s.auth.toRegister : s.auth.toLogin}
              </button>
              <button
                type="button"
                className="langtoggle"
                style={{ borderColor: "var(--line)", color: "var(--night)" }}
                onClick={() => setLang(lang === "es" ? "en" : "es")}
              >
                {lang === "es" ? "EN" : "ES"}
              </button>
            </div>
          </form>

          <div style={{ marginTop: 18, textAlign: "center" }}>
            <button
              className="btn btn--ghost"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  setEmail(DEMO_EMAIL);
                  setPassword(DEMO_PASSWORD);
                  await signIn(DEMO_EMAIL, DEMO_PASSWORD);
                })
              }
            >
              {s.auth.demo}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
