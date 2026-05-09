import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "inibsa.salesDelegateSession";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: "Delegado de Ventas";
};

export type AuthCredentials = {
  email: string;
  password: string;
};

type StoredSession = {
  token: string;
  user: AuthUser;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (credentials: AuthCredentials) => Promise<AuthUser>;
  register: (credentials: AuthCredentials) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredSession(): StoredSession | null {
  const rawSession = localStorage.getItem(STORAGE_KEY);

  if (!rawSession) {
    return null;
  }

  try {
    return JSON.parse(rawSession) as StoredSession;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function createMockUser(email: string): AuthUser {
  return {
    id: "delegate-001",
    name: "Delegado de Ventas",
    email,
    role: "Delegado de Ventas",
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const storedSession = readStoredSession();
  const [token, setToken] = useState<string | null>(storedSession?.token ?? null);
  const [user, setUser] = useState<AuthUser | null>(storedSession?.user ?? null);

  const saveSession = useCallback((nextUser: AuthUser) => {
    const nextSession = {
      token: `mock-token-${Date.now()}`,
      user: nextUser,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
    setToken(nextSession.token);
    setUser(nextSession.user);
  }, []);

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const nextUser = createMockUser(credentials.email.trim() || "delegado@inibsa.local");
      saveSession(nextUser);
      return nextUser;
    },
    [saveSession],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      const nextUser = createMockUser(credentials.email.trim() || "delegado@inibsa.local");
      saveSession(nextUser);
      return nextUser;
    },
    [saveSession],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading: false,
      login,
      register,
      logout,
    }),
    [login, logout, register, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
