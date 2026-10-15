import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";
import type { FamilyContact } from "../lib/types";

export function Family() {
  const { s } = useI18n();
  const { token } = useAuth();
  const [items, setItems] = useState<FamilyContact[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [rel, setRel] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setItems(await api<FamilyContact[]>("/api/family", { token }));
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
      await api("/api/family", {
        method: "POST",
        token,
        body: { name, email, relationship_label: rel },
      });
      setName("");
      setEmail("");
      setRel("");
      await load();
    } catch {
      setError(s.common.genericError);
    }
  }

  async function remove(id: string) {
    await api(`/api/family/${id}`, { method: "DELETE", token });
    await load();
  }

  return (
    <>
      <h1 className="mt0">{s.family.title}</h1>
      <p className="lead">{s.family.lead}</p>

      <section className="section">
        {items.length === 0 ? (
          <p className="muted">{s.family.empty}</p>
        ) : (
          items.map((c) => (
            <div className="record" key={c.id}>
              <div>
                <div className="record__title">{c.name}</div>
                <div className="record__meta">
                  {c.email}
                  {c.relationship_label ? ` · ${c.relationship_label}` : ""}
                </div>
              </div>
              <button className="btn btn--quiet" onClick={() => remove(c.id)}>
                {s.common.remove}
              </button>
            </div>
          ))
        )}
      </section>

      <form className="card section" onSubmit={add}>
        <h2 className="mt0">{s.family.addTitle}</h2>
        {error && (
          <div className="flash flash--error" role="alert">
            {error}
          </div>
        )}
        <div className="grid-2">
          <label className="field">
            <span>{s.family.name}</span>
            <input
              className="input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="field">
            <span>{s.family.email}</span>
            <input
              className="input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
        </div>
        <label className="field">
          <span>
            {s.family.relationship} <span className="muted">({s.common.optional})</span>
          </span>
          <input
            className="input"
            value={rel}
            onChange={(e) => setRel(e.target.value)}
          />
          <span className="hint">{s.family.relationshipHint}</span>
        </label>
        <button className="btn" type="submit">
          {s.common.add}
        </button>
      </form>
    </>
  );
}
