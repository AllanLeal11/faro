import { useI18n } from "../lib/i18n";

// This screen's longer-form copy lives here in both languages; it's
// explanatory content, not reused UI chrome.
const CONTENT = {
  es: {
    stepsTitle: "Cómo revisa un mensaje",
    steps: [
      {
        t: "Lee el mensaje",
        d: "Extrae enlaces, dominios, teléfonos y qué te están pidiendo hacer.",
      },
      {
        t: "Verifica sin adivinar",
        d: "Comprobaciones automáticas buscan dominios imitadores, pedidos de códigos, pagos con cripto o tarjetas de regalo, y trucos de texto.",
      },
      {
        t: "Busca evidencia",
        d: "Contrasta el remitente con tu círculo de confianza y con fuentes públicas.",
      },
      {
        t: "Da un veredicto con pruebas",
        d: "Un modelo de IA explica el riesgo en lenguaje simple, citando únicamente la evidencia encontrada.",
      },
    ],
    rulesTitle: "Dos reglas que lo hacen confiable",
    rules: [
      "La IA no puede inventar evidencia: toda razón se apoya en una verificación real.",
      "Si una verificación detecta una señal grave, el riesgo no puede bajar de «Peligro».",
    ],
    alexaTitle: "También por voz y con Alexa+",
    alexaText:
      "Faro expone sus herramientas por MCP (Streamable HTTP), así que un asistente como Alexa+ puede revisar un mensaje, gestionar tu círculo de confianza o avisar a un familiar.",
    privacyTitle: "Tu privacidad",
    privacyText:
      "Faro nunca abre los enlaces del mensaje y no guarda lo que pegás. Solo se guarda tu círculo de confianza y tus contactos familiares.",
  },
  en: {
    stepsTitle: "How it checks a message",
    steps: [
      {
        t: "Reads the message",
        d: "Extracts links, domains, phone numbers and what you're being asked to do.",
      },
      {
        t: "Verifies without guessing",
        d: "Automated checks look for look-alike domains, requests for codes, crypto or gift-card payments, and text tricks.",
      },
      {
        t: "Looks for evidence",
        d: "Compares the sender against your trusted circle and public sources.",
      },
      {
        t: "Gives a verdict with proof",
        d: "An AI model explains the risk in plain language, citing only the evidence found.",
      },
    ],
    rulesTitle: "Two rules that make it trustworthy",
    rules: [
      "The AI cannot invent evidence: every reason rests on a real check.",
      "If a check finds a severe signal, the risk can't drop below “Danger”.",
    ],
    alexaTitle: "Also by voice and with Alexa+",
    alexaText:
      "Faro exposes its tools over MCP (Streamable HTTP), so an assistant like Alexa+ can check a message, manage your trusted circle, or alert a family member.",
    privacyTitle: "Your privacy",
    privacyText:
      "Faro never opens the links in a message and doesn't store what you paste. Only your trusted circle and family contacts are saved.",
  },
};

export function HowItWorks() {
  const { s, lang } = useI18n();
  const c = CONTENT[lang];

  return (
    <>
      <h1 className="mt0">{s.how.title}</h1>
      <p className="lead">{s.how.lead}</p>

      <section className="section">
        <h2>{c.stepsTitle}</h2>
        <ol className="stack" style={{ paddingLeft: "1.1em" }}>
          {c.steps.map((step) => (
            <li key={step.t}>
              <strong>{step.t}.</strong> {step.d}
            </li>
          ))}
        </ol>
      </section>

      <section className="card section">
        <h2 className="mt0">{c.rulesTitle}</h2>
        <ul className="stack" style={{ paddingLeft: "1.1em" }}>
          {c.rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </section>

      <section className="section">
        <h2>{c.alexaTitle}</h2>
        <p>{c.alexaText}</p>
      </section>

      <section className="section">
        <h2>{c.privacyTitle}</h2>
        <p>{c.privacyText}</p>
      </section>
    </>
  );
}
