import { Link } from "react-router-dom";
import { useI18n } from "../lib/i18n";

export function Footer() {
  const { s } = useI18n();
  return (
    <footer className="sitefoot">
      <div className="wrap">
        <nav className="sitefoot__links" aria-label="Legal">
          <Link to="/privacy">{s.footer.privacy}</Link>
          <span aria-hidden="true">·</span>
          <Link to="/terms">{s.footer.terms}</Link>
        </nav>
        <p className="muted mt0">
          {s.footer.madeBy} {s.footer.noTracking}
        </p>
      </div>
    </footer>
  );
}
