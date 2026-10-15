import { useRef, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import type { AnalysisResult } from "../lib/types";
import { Verdict } from "../components/Verdict";
import { MicIcon } from "../components/icons";

// Minimal typing for the Web Speech API (not in the standard DOM lib).
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: (e: { results: { 0: { 0: { transcript: string } } } }) => void;
  onerror: () => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
}
type SRCtor = new () => SpeechRecognitionLike;

function getRecognition(): SRCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SRCtor;
    webkitSpeechRecognition?: SRCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function Voice() {
  const { s, lang } = useI18n();
  const { token } = useAuth();
  const [listening, setListening] = useState(false);
  const [heard, setHeard] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const recRef = useRef<SpeechRecognitionLike | null>(null);

  const Ctor = getRecognition();
  const supported = Ctor !== null;
  const locale = lang === "es" ? "es-CR" : "en-US";

  function speak(text: string) {
    try {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = locale;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    } catch {
      /* speech synthesis is a nice-to-have */
    }
  }

  async function analyze(text: string) {
    try {
      const res = await api<AnalysisResult>("/api/check", {
        method: "POST",
        token,
        body: { message: text, language: lang },
      });
      setResult(res);
      const word =
        res.risk_level === "high"
          ? s.check.risk.high
          : res.risk_level === "medium"
            ? s.check.risk.medium
            : s.check.risk.low;
      speak(`${word}. ${res.explanation} ${res.recommended_action}`);
    } catch {
      /* keep the UI calm; the Check screen surfaces errors in detail */
    }
  }

  function start() {
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = locale;
    rec.interimResults = false;
    rec.continuous = false;
    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setHeard(transcript);
      analyze(transcript);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recRef.current = rec;
    setResult(null);
    setHeard("");
    setListening(true);
    rec.start();
  }

  function stop() {
    recRef.current?.stop();
    setListening(false);
  }

  return (
    <>
      <h1 className="mt0">{s.voice.title}</h1>
      <p className="lead">{s.voice.lead}</p>

      {!supported ? (
        <div className="flash flash--error">{s.voice.unsupported}</div>
      ) : (
        <div className="voice-stage">
          <button
            className={`mic${listening ? " listening" : ""}`}
            onClick={listening ? stop : start}
            aria-pressed={listening}
            aria-label={listening ? s.voice.listening : s.voice.start}
          >
            <MicIcon />
          </button>
          <p className="transcript" aria-live="polite">
            {listening
              ? s.voice.listening
              : heard
                ? `${s.voice.youSaid} “${heard}”`
                : s.voice.start}
          </p>
        </div>
      )}

      {result && <Verdict result={result} />}

      <p className="muted section">{s.voice.note}</p>
    </>
  );
}
