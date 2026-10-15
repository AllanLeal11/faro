import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";
import { Footer } from "../components/Footer";
import { BeaconMark } from "../components/icons";

// Contact for data requests. Uses the Vértice Digital domain; confirm the
// mailbox exists (or change it) before going public.
const CONTACT = "contacto@verticedigital.space";

type Section = { h: string; p: string[] };
type Doc = { title: string; updated: string; sections: Section[] };

const LEGAL: Record<"es" | "en", { privacy: Doc; terms: Doc }> = {
  es: {
    privacy: {
      title: "Política de privacidad",
      updated: "Última actualización: 15 de octubre de 2026",
      sections: [
        {
          h: "Qué datos guardamos",
          p: [
            "Para darte el servicio guardamos: tu correo, tu contraseña (siempre cifrada, nunca en texto), tu círculo de confianza (bancos y empresas que registrás), tus contactos familiares, y datos mínimos de las alertas que enviás (nivel de riesgo y fecha).",
          ],
        },
        {
          h: "Qué NO guardamos",
          p: [
            "Los mensajes que analizás no se almacenan. Se procesan en el momento para darte el resultado y luego se descartan. Faro tampoco abre ni visita los enlaces de esos mensajes.",
          ],
        },
        {
          h: "Para qué usamos tus datos",
          p: [
            "Únicamente para que Faro funcione: analizar mensajes, detectar quién se hace pasar por tus entidades de confianza y avisar a tus familiares cuando lo pedís. No vendemos tus datos ni los usamos para publicidad.",
          ],
        },
        {
          h: "Con quién se comparten",
          p: [
            "Solo con los proveedores que hacen funcionar el servicio: Amazon Web Services (análisis con inteligencia artificial y envío de correos de alerta). No usamos analíticas de terceros.",
          ],
        },
        {
          h: "Seguridad",
          p: [
            "Las contraseñas se protegen con Argon2id, la información viaja cifrada (HTTPS) y cada persona solo puede acceder a sus propios datos.",
          ],
        },
        {
          h: "Tus derechos",
          p: [
            "De acuerdo con la Ley 8968 de Costa Rica, podés pedir acceder, corregir o eliminar tus datos. Escribinos a " +
              CONTACT +
              " y atenderemos tu solicitud.",
          ],
        },
        {
          h: "Cookies",
          p: [
            "Faro solo usa el almacenamiento técnico necesario para funcionar. No usamos cookies de rastreo ni perfiles publicitarios.",
          ],
        },
        {
          h: "Cambios",
          p: [
            "Podemos actualizar esta política. Si el cambio es importante, lo indicaremos en esta página con una nueva fecha.",
          ],
        },
      ],
    },
    terms: {
      title: "Términos y condiciones",
      updated: "Última actualización: 15 de octubre de 2026",
      sections: [
        {
          h: "Qué es Faro",
          p: [
            "Faro es una herramienta de ayuda para reconocer posibles estafas. Es una ayuda, no un reemplazo de tu banco ni asesoría legal o financiera. La decisión final siempre es tuya: ante cualquier duda, confirmá llamando a la entidad por su número oficial.",
          ],
        },
        {
          h: "Uso aceptable",
          p: [
            "Usá Faro de buena fe. No lo uses para fines ilegales, para dañar a terceros ni para abusar del servicio.",
          ],
        },
        {
          h: "Sin garantías",
          p: [
            "Faro hace su mejor esfuerzo, pero ningún sistema es perfecto: puede marcar como seguro un mensaje peligroso, o al revés. No garantizamos que detecte todas las estafas. Usalo como una capa más de protección, no como la única.",
          ],
        },
        {
          h: "Limitación de responsabilidad",
          p: [
            "En la medida que la ley lo permita, no somos responsables por pérdidas derivadas de decisiones que tomes a partir de un resultado de Faro.",
          ],
        },
        {
          h: "Cuenta de demostración",
          p: [
            "La cuenta de demostración es pública y sus datos se reinician periódicamente. No guardes información real en ella.",
          ],
        },
        {
          h: "Ley aplicable y contacto",
          p: [
            "Estos términos se rigen por las leyes de Costa Rica. Para consultas: " +
              CONTACT +
              ".",
          ],
        },
      ],
    },
  },
  en: {
    privacy: {
      title: "Privacy policy",
      updated: "Last updated: October 15, 2026",
      sections: [
        {
          h: "What we store",
          p: [
            "To provide the service we store: your email, your password (always hashed, never in plain text), your trusted circle (banks and companies you register), your family contacts, and minimal alert metadata (risk level and date).",
          ],
        },
        {
          h: "What we do NOT store",
          p: [
            "The messages you analyze are not stored. They are processed in the moment to give you a result and then discarded. Faro also never opens or visits the links in those messages.",
          ],
        },
        {
          h: "How we use your data",
          p: [
            "Only to make Faro work: analyzing messages, detecting who impersonates your trusted entities, and alerting your family when you ask. We don't sell your data or use it for advertising.",
          ],
        },
        {
          h: "Who it's shared with",
          p: [
            "Only the providers that run the service: Amazon Web Services (AI analysis and sending alert emails). We use no third-party analytics.",
          ],
        },
        {
          h: "Security",
          p: [
            "Passwords are protected with Argon2id, data travels encrypted (HTTPS), and each person can only access their own data.",
          ],
        },
        {
          h: "Your rights",
          p: [
            "Under Costa Rica's Law 8968, you may request access to, correction of, or deletion of your data. Write to " +
              CONTACT +
              " and we'll handle your request.",
          ],
        },
        {
          h: "Cookies",
          p: [
            "Faro only uses the technical storage needed to function. We use no tracking cookies or advertising profiles.",
          ],
        },
        {
          h: "Changes",
          p: [
            "We may update this policy. If a change is significant, we'll note it on this page with a new date.",
          ],
        },
      ],
    },
    terms: {
      title: "Terms and conditions",
      updated: "Last updated: October 15, 2026",
      sections: [
        {
          h: "What Faro is",
          p: [
            "Faro is a tool that helps you recognize possible scams. It's an aid, not a replacement for your bank or for legal or financial advice. The final decision is always yours: when in doubt, confirm by calling the organization at its official number.",
          ],
        },
        {
          h: "Acceptable use",
          p: [
            "Use Faro in good faith. Don't use it for illegal purposes, to harm others, or to abuse the service.",
          ],
        },
        {
          h: "No warranty",
          p: [
            "Faro does its best, but no system is perfect: it may mark a dangerous message as safe, or vice versa. We don't guarantee it catches every scam. Use it as one more layer of protection, not the only one.",
          ],
        },
        {
          h: "Limitation of liability",
          p: [
            "To the extent permitted by law, we aren't liable for losses arising from decisions you make based on a Faro result.",
          ],
        },
        {
          h: "Demo account",
          p: [
            "The demo account is public and its data resets periodically. Don't store real information in it.",
          ],
        },
        {
          h: "Governing law and contact",
          p: [
            "These terms are governed by the laws of Costa Rica. For questions: " +
              CONTACT +
              ".",
          ],
        },
      ],
    },
  },
};

export function Legal({ kind }: { kind: "privacy" | "terms" }) {
  const { s, lang } = useI18n();
  const doc = LEGAL[lang][kind];

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__inner">
          <Link to="/" className="brand">
            <span className="brand__beam">
              <BeaconMark />
            </span>
            Faro
          </Link>
        </div>
      </header>
      <main className="main" id="main">
        <div className="wrap center-narrow legal">
          <Link to="/" className="backlink">
            ← {s.footer.back}
          </Link>
          <h1 className="mt0">{doc.title}</h1>
          <p className="muted">{doc.updated}</p>
          {doc.sections.map((sec) => (
            <section key={sec.h}>
              <h2>{sec.h}</h2>
              {sec.p.map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </section>
          ))}
        </div>
        <Footer />
      </main>
    </div>
  );
}
