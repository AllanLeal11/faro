import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Lang } from "./types";

// Copy lives here, in both languages. Written from the user's perspective, in
// plain words — the interface should feel calm and clear, not technical.
const ES = {
  tagline: "Tu guía contra las estafas",
  nav: {
    check: "Revisar",
    trusted: "Mi círculo",
    family: "Familia",
    voice: "Voz",
    how: "Cómo funciona",
    logout: "Salir",
  },
  common: {
    loading: "Revisando…",
    save: "Guardar",
    add: "Agregar",
    remove: "Quitar",
    cancel: "Cancelar",
    optional: "opcional",
    networkError: "No se pudo conectar. Revisá tu internet e intentá de nuevo.",
    genericError: "Algo salió mal. Intentá de nuevo.",
  },
  auth: {
    welcome: "Entrá a Faro",
    subtitle: "Revisá si un mensaje es una estafa, con evidencia clara.",
    email: "Correo",
    password: "Contraseña",
    enter: "Entrar",
    create: "Crear cuenta",
    toRegister: "¿No tenés cuenta? Crear una",
    toLogin: "¿Ya tenés cuenta? Entrar",
    demo: "Entrar con la cuenta de demostración",
    badCreds: "Correo o contraseña incorrectos.",
    tooMany: "Demasiados intentos. Esperá un minuto.",
    passwordHint: "Mínimo 8 caracteres.",
  },
  check: {
    heroTitle: "¿Te llegó un mensaje raro?",
    heroSub: "Pególo aquí. Faro te dice si es una estafa, por qué, y qué hacer.",
    label: "Mensaje sospechoso",
    placeholder: "Ejemplo: «Su cuenta SINPE fue bloqueada. Ingrese aquí…»",
    submit: "Revisar mensaje",
    privacy: "Faro no abre los enlaces del mensaje y no guarda lo que pegás.",
    empty: "Primero pegá o escribí el mensaje que te llegó.",
    risk: {
      high: "Peligro",
      medium: "Cuidado",
      low: "Parece seguro",
      highSub: "Es muy probable que sea una estafa.",
      mediumSub: "Tiene señales sospechosas.",
      lowSub: "No se encontraron señales fuertes de estafa.",
    },
    whatToDo: "Qué hacer",
    why: "Por qué",
    verify: "Pregunta para verificar",
    partial: "Análisis con verificaciones automáticas (la IA no estuvo disponible).",
    alertFamily: "Avisar a un familiar",
    confidence: "Seguridad del análisis",
  },
  trusted: {
    title: "Mi círculo de confianza",
    lead: "Registrá tu banco y las empresas que conocés. Faro avisa cuando alguien se hace pasar por ellos.",
    name: "Nombre",
    kind: "Tipo",
    kinds: { bank: "Banco", company: "Empresa", contact: "Persona" },
    domains: "Sitios oficiales",
    domainsHint: "Separá con comas. Ej: baccredomatic.com",
    phones: "Teléfonos oficiales",
    emails: "Correos oficiales",
    addTitle: "Agregar al círculo",
    empty: "Todavía no agregaste nada. Empezá por tu banco.",
  },
  family: {
    title: "Familia de confianza",
    lead: "Agregá a alguien que pueda ayudarte a verificar un mensaje antes de actuar.",
    name: "Nombre",
    email: "Correo",
    relationship: "Parentesco",
    relationshipHint: "Ej: hija, hijo, vecino",
    addTitle: "Agregar familiar",
    empty: "Agregá a un familiar de confianza para poder avisarle.",
    pick: "¿A quién querés avisar?",
    sent: "Aviso enviado.",
    noContacts: "Primero agregá un familiar en la pantalla de Familia.",
  },
  voice: {
    title: "Revisar por voz",
    lead: "Tocá el botón y leé en voz alta el mensaje que te llegó. Faro te responde hablando.",
    start: "Hablar",
    listening: "Escuchando…",
    unsupported:
      "Tu navegador no permite entrada por voz. Podés usar la pantalla de Revisar.",
    youSaid: "Dijiste:",
    note: "Esta pantalla simula una experiencia de voz tipo Alexa+, usando las mismas herramientas que Faro ofrece por MCP.",
  },
  how: {
    title: "Cómo funciona Faro",
    lead: "Faro no adivina. Cada veredicto se apoya en evidencia que podés revisar.",
  },
};

const EN: typeof ES = {
  tagline: "Your guide against scams",
  nav: {
    check: "Check",
    trusted: "My circle",
    family: "Family",
    voice: "Voice",
    how: "How it works",
    logout: "Sign out",
  },
  common: {
    loading: "Checking…",
    save: "Save",
    add: "Add",
    remove: "Remove",
    cancel: "Cancel",
    optional: "optional",
    networkError: "Couldn't connect. Check your internet and try again.",
    genericError: "Something went wrong. Try again.",
  },
  auth: {
    welcome: "Sign in to Faro",
    subtitle: "Check whether a message is a scam, with clear evidence.",
    email: "Email",
    password: "Password",
    enter: "Sign in",
    create: "Create account",
    toRegister: "No account? Create one",
    toLogin: "Have an account? Sign in",
    demo: "Sign in with the demo account",
    badCreds: "Invalid email or password.",
    tooMany: "Too many attempts. Wait a minute.",
    passwordHint: "At least 8 characters.",
  },
  check: {
    heroTitle: "Got a message that feels off?",
    heroSub: "Paste it here. Faro tells you if it's a scam, why, and what to do.",
    label: "Suspicious message",
    placeholder: "Example: “Your account was blocked. Sign in here…”",
    submit: "Check message",
    privacy: "Faro never opens the links in the message and doesn't store what you paste.",
    empty: "First paste or type the message you received.",
    risk: {
      high: "Danger",
      medium: "Caution",
      low: "Looks safe",
      highSub: "This is very likely a scam.",
      mediumSub: "It has suspicious signs.",
      lowSub: "No strong scam signals were found.",
    },
    whatToDo: "What to do",
    why: "Why",
    verify: "Question to verify",
    partial: "Analyzed with automated checks (the AI was unavailable).",
    alertFamily: "Alert a family member",
    confidence: "Analysis confidence",
  },
  trusted: {
    title: "My trusted circle",
    lead: "Add your bank and the companies you know. Faro warns you when someone impersonates them.",
    name: "Name",
    kind: "Type",
    kinds: { bank: "Bank", company: "Company", contact: "Person" },
    domains: "Official websites",
    domainsHint: "Separate with commas. E.g. baccredomatic.com",
    phones: "Official phone numbers",
    emails: "Official emails",
    addTitle: "Add to circle",
    empty: "Nothing added yet. Start with your bank.",
  },
  family: {
    title: "Trusted family",
    lead: "Add someone who can help you verify a message before you act.",
    name: "Name",
    email: "Email",
    relationship: "Relationship",
    relationshipHint: "E.g. daughter, son, neighbor",
    addTitle: "Add family member",
    empty: "Add a trusted family member so you can alert them.",
    pick: "Who do you want to alert?",
    sent: "Alert sent.",
    noContacts: "First add a family member on the Family screen.",
  },
  voice: {
    title: "Check by voice",
    lead: "Tap the button and read the message out loud. Faro answers back by speaking.",
    start: "Speak",
    listening: "Listening…",
    unsupported: "Your browser doesn't support voice input. You can use the Check screen.",
    youSaid: "You said:",
    note: "This screen simulates an Alexa+-style voice experience, using the same tools Faro exposes over MCP.",
  },
  how: {
    title: "How Faro works",
    lead: "Faro doesn't guess. Every verdict rests on evidence you can review.",
  },
};

type Strings = typeof ES;

interface Ctx {
  lang: Lang;
  setLang: (l: Lang) => void;
  s: Strings;
}

const LangContext = createContext<Ctx | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("es");
  const value = useMemo<Ctx>(
    () => ({ lang, setLang, s: lang === "es" ? ES : EN }),
    [lang],
  );
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useI18n must be used within LanguageProvider");
  return ctx;
}
