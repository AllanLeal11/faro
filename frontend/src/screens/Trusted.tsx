import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import type { TrustedEntity, TrustedKind } from "../lib/types";

const splitList = (v: string) =>
  v
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export function Trusted() {
  const { s } = useI18n();
  const { token } = useAuth();
  const [items, setItems] = useState<TrustedEntity[]>([]);
  const [kind, setKind] = useState<TrustedKind>("bank");
  const [name, setName] = useState("");
  const [domains, setDomains] = useState("");
  const [phones, setPhones] = useState("");
  const [emails, setEmails] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setItems(await api<TrustedEntity[]>("/api/trusted", { token }));
    } catch {
      setError(s.common.genericError);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/api/trusted", {
        method: "POST",
        token,
        body: {
          kind,
          name,
          domains: splitList(domains),
          phones: splitList(phones),
          emails: splitList(emails),
        },
      });
      setName("");
      setDomains("");
      setPhones("");
      setEmails("");
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 422
          ? s.trusted.domainsHint
          : s.common.genericError,
      );
    }
  }

  async function remove(id: string) {
    await api(`/api/trusted/${id}`, { method: "DELETE", token });
    await load();
  }

  return (
    <>
      <h1 className="mt0">{s.trusted.title}</h1>
      <p className="lead">{s.trusted.lead}</p>

      <section className="section">
        {items.length === 0 ? (
          <p className="muted">{s.trusted.empty}</p>
        ) : (
          items.map((e) => (
            <div className="record" key={e.id}>
              <div>
                <div className="record__title">
                  <span className="tag">{s.trusted.kinds[e.kind]}</span>
                  {e.name}
                </div>
                {e.domains.length > 0 && (
                  <div className="record__meta">{e.domains.join(", ")}</div>
                )}
              </div>
              <button className="btn btn--quiet" onClick={() => remove(e.id)}>
                {s.common.remove}
              </button>
            </div>
          ))
        )}
      </section>

      <form className="card section" onSubmit={add}>
        <h2 className="mt0">{s.trusted.addTitle}</h2>
        {error && (
          <div className="flash flash--error" role="alert">
            {error}
          </div>
        )}
        <div className="grid-2">
          <label className="field">
            <span>{s.trusted.kind}</span>
            <select
              className="select"
              value={kind}
              onChange={(e) => setKind(e.target.value as TrustedKind)}
            >
              <option value="bank">{s.trusted.kinds.bank}</option>
              <option value="company">{s.trusted.kinds.company}</option>
              <option value="contact">{s.trusted.kinds.contact}</option>
            </select>
          </label>
          <label className="field">
            <span>{s.trusted.name}</span>
            <input
              className="input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        </div>
        <label className="field">
          <span>{s.trusted.domains}</span>
          <input
            className="input"
            value={domains}
            onChange={(e) => setDomains(e.target.value)}
          />
          <span className="hint">{s.trusted.domainsHint}</span>
        </label>
        <div className="grid-2">
          <label className="field">
            <span>
              {s.trusted.phones} <span className="muted">({s.common.optional})</span>
            </span>
            <input
              className="input"
              value={phones}
              onChange={(e) => setPhones(e.target.value)}
            />
          </label>
          <label className="field">
            <span>
              {s.trusted.emails} <span className="muted">({s.common.optional})</span>
            </span>
            <input
              className="input"
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
            />
          </label>
        </div>
        <button className="btn" type="submit">
          {s.common.add}
        </button>
      </form>
    </>
  );
}
