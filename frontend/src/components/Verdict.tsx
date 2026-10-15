import type { AnalysisResult } from "../lib/types";
import { useI18n } from "../lib/i18n";
import { AlertTriangle, Dot, OctagonAlert, ShieldCheck } from "./icons";

interface Props {
  result: AnalysisResult;
  onAlertFamily?: () => void;
}

export function Verdict({ result, onAlertFamily }: Props) {
  const { s } = useI18n();
  const level = result.risk_level;
  const r = s.check.risk;

  const word = level === "high" ? r.high : level === "medium" ? r.medium : r.low;
  const sub =
    level === "high" ? r.highSub : level === "medium" ? r.mediumSub : r.lowSub;
  const Icon =
    level === "high" ? OctagonAlert : level === "medium" ? AlertTriangle : ShieldCheck;

  const pct = Math.round(result.confidence * 100);

  return (
    <section className={`verdict verdict--${level}`} aria-live="polite">
      <div className="verdict__banner">
        <Icon />
        <div>
          <div className="verdict__word">{word}</div>
          <div className="verdict__sub">{sub}</div>
        </div>
      </div>

      <div className="verdict__body">
        <p className="mt0" style={{ fontSize: "1.15rem" }}>
          {result.explanation}
        </p>

        <div className="verdict__action">
          <strong style={{ whiteSpace: "nowrap" }}>{s.check.whatToDo}:</strong>
          <span>{result.recommended_action}</span>
        </div>

        {result.evidence.length > 0 && (
          <>
            <h3>{s.check.why}</h3>
            <ul className="evidence">
              {result.evidence.map((e) => (
                <li key={e.id} className={e.severe ? "sev" : ""}>
                  <span className="evidence__dot">
                    <Dot color={e.severe ? "#c0392b" : "#46586a"} />
                  </span>
                  <span className="evidence__text">
                    {e.detail}
                    {e.source_url && (
                      <span className="evidence__src">
                        {" "}
                        <a
                          href={e.source_url}
                          target="_blank"
                          rel="noopener noreferrer nofollow"
                        >
                          {new URL(e.source_url).hostname}
                        </a>
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {result.verification_question && (
          <p style={{ marginTop: "18px" }}>
            <strong>{s.check.verify}:</strong> {result.verification_question}
          </p>
        )}

        <div style={{ marginTop: "18px" }}>
          <div className="hint">
            {s.check.confidence}: {pct}%
          </div>
          <div
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            style={{
              height: 10,
              background: "var(--line)",
              borderRadius: 999,
              overflow: "hidden",
              marginTop: 4,
            }}
          >
            <div
              style={{
                width: `${pct}%`,
                height: "100%",
                background: "var(--night)",
              }}
            />
          </div>
        </div>

        {onAlertFamily && (
          <div className="btn-row" style={{ marginTop: "20px" }}>
            <button className="btn btn--ghost" onClick={onAlertFamily}>
              {s.check.alertFamily}
            </button>
          </div>
        )}

        {result.partial && <p className="partial-note">{s.check.partial}</p>}
      </div>
    </section>
  );
}
