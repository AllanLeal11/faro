import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import type { AnalysisResult, FamilyContact } from "../lib/types";
import { Verdict } from "../components/Verdict";

export function Check() {
  const { s, lang } = useI18n();
  const { token } = useAuth();
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAlert, setShowAlert] = useState(false);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) {
      setError(s.check.empty);
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    setShowAlert(false);
    try {
      const res = await api<AnalysisResult>("/api/check", {
        method: "POST",
        token,
        body: { message, language: lang },
      });
      setResult(res);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? s.common.networkError
          : s.common.genericError,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="beacon-panel">
        <h1 className="mt0">{s.check.heroTitle}</h1>
        <p>{s.check.heroSub}</p>
      </div>

      <form onSubmit={check} className="section">
        <label className="field">
          <span>{s.check.label}</span>
          <textarea
            className="textarea"
            placeholder={s.check.placeholder}
            value={message}
            maxLength={5000}
            onChange={(e) => setMessage(e.target.value)}
          />
          <span className="hint">{s.check.privacy}</span>
        </label>

        {error && (
          <div className="flash flash--error" role="alert">
            {error}
          </div>
        )}

        <button className="btn btn--big" type="submit" disabled={busy}>
          {busy ? s.common.loading : s.check.submit}
        </button>
      </form>

      {result && (
        <>
          <Verdict result={result} onAlertFamily={() => setShowAlert((v) => !v)} />
          {showAlert && (
            <AlertFamily
              token={token}
              riskLevel={result.risk_level}
              verificationQuestion={result.verification_question}
            />
          )}
        </>
      )}
    </>
  );
}

function AlertFamily({
  token,
  riskLevel,
  verificationQuestion,
}: {
  token: string | null;
  riskLevel: string;
  verificationQuestion: string;
}) {
  const { s } = useI18n();
  const [contacts, setContacts] = useState<FamilyContact[] | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Load contacts once when the panel first opens.
  if (contacts === null && !loading && !error) {
    setLoading(true);
    api<FamilyContact[]>("/api/family", { token })
      .then((c) => setContacts(c))
      .catch(() => setError(s.common.genericError))
      .finally(() => setLoading(false));
  }

  async function send(contact: FamilyContact) {
    setError(null);
    try {
      await api("/api/alert", {
        method: "POST",
        token,
        body: {
          family_contact_id: contact.id,
          risk_level: riskLevel,
          verification_question: verificationQuestion,
        },
      });
      setSentTo(contact.name);
    } catch {
      setError(s.common.genericError);
    }
  }

  return (
    <div className="card section">
      <h3 className="mt0">{s.family.pick}</h3>
      {error && (
        <div className="flash flash--error" role="alert">
          {error}
        </div>
      )}
      {sentTo ? (
        <div className="flash flash--ok" role="status">
          {s.family.sent}
        </div>
      ) : contacts && contacts.length === 0 ? (
        <p className="muted">{s.family.noContacts}</p>
      ) : (
        contacts?.map((c) => (
          <div className="record" key={c.id}>
            <div>
              <div className="record__title">{c.name}</div>
              <div className="record__meta">{c.email}</div>
            </div>
            <button className="btn" onClick={() => send(c)}>
              {s.check.alertFamily}
            </button>
          </div>
        ))
      )}
    </div>
  );
}
