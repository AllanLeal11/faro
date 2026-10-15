import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { TokenResponse, User } from "./types";

// The access token is held in memory only — never in localStorage or a cookie
// (see docs/security.md). A page refresh signs the user out; the demo button
// makes signing back in a single tap.

interface AuthCtx {
  user: User | null;
  token: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, language: string) => Promise<void>;
  signOut: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await api<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, language: string) => {
      const res = await api<TokenResponse>("/api/auth/register", {
        method: "POST",
        body: { email, password, language },
      });
      setToken(res.access_token);
      setUser(res.user);
    },
    [],
  );

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({ user, token, signIn, register, signOut }),
    [user, token, signIn, register, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
