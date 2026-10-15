import { NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth";
import { useI18n } from "./lib/i18n";
import { BeaconMark } from "./components/icons";
import { Login } from "./screens/Login";
import { Check } from "./screens/Check";
import { Trusted } from "./screens/Trusted";
import { Family } from "./screens/Family";
import { Voice } from "./screens/Voice";
import { HowItWorks } from "./screens/HowItWorks";
import { Legal } from "./screens/Legal";
import { Footer } from "./components/Footer";

function TopBar() {
  const { s, lang, setLang } = useI18n();
  const { signOut } = useAuth();
  return (
    <header className="topbar">
      <div className="topbar__inner">
        <NavLink to="/" className="brand">
          <span className="brand__beam">
            <BeaconMark />
          </span>
          Faro
        </NavLink>
        <nav className="nav" aria-label="Principal">
          <NavLink to="/" end>
            {s.nav.check}
          </NavLink>
          <NavLink to="/trusted">{s.nav.trusted}</NavLink>
          <NavLink to="/family">{s.nav.family}</NavLink>
          <NavLink to="/voice">{s.nav.voice}</NavLink>
          <NavLink to="/how">{s.nav.how}</NavLink>
        </nav>
        <div className="btn-row">
          <button
            className="langtoggle"
            onClick={() => setLang(lang === "es" ? "en" : "es")}
            aria-label={lang === "es" ? "Switch to English" : "Cambiar a español"}
          >
            {lang === "es" ? "EN" : "ES"}
          </button>
          <button className="langtoggle" onClick={signOut}>
            {s.nav.logout}
          </button>
        </div>
      </div>
    </header>
  );
}

function AppShell() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Saltar al contenido
      </a>
      <TopBar />
      <main className="main" id="main">
        <div className="wrap">
          <Routes>
            <Route path="/" element={<Check />} />
            <Route path="/trusted" element={<Trusted />} />
            <Route path="/family" element={<Family />} />
            <Route path="/voice" element={<Voice />} />
            <Route path="/how" element={<HowItWorks />} />
          </Routes>
        </div>
        <Footer />
      </main>
    </div>
  );
}

export function App() {
  const { token } = useAuth();

  // Legal pages are public — reachable with or without a session.
  return (
    <Routes>
      <Route path="/privacy" element={<Legal kind="privacy" />} />
      <Route path="/terms" element={<Legal kind="terms" />} />
      <Route path="/*" element={token ? <AppShell /> : <Login />} />
    </Routes>
  );
}
