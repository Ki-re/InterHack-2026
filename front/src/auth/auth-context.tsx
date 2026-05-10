import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "inibsa.salesDelegateSession";

export type UserRole = "sales_delegate" | "regional_manager";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
};

export type AuthCredentials = {
  email: string;
  password: string;
  role?: UserRole;
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
    const parsed = JSON.parse(rawSession) as StoredSession;
    const role = parsed.user.role === "regional_manager" ? "regional_manager" : "sales_delegate";
    return {
      ...parsed,
      user: {
        ...parsed.user,
        role,
      },
    };
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function createMockUser(email: string, role: UserRole): AuthUser {
  return {
    id: role === "regional_manager" ? "regional-001" : "delegate-001",
    name: role === "regional_manager" ? "Regional Manager" : "Delegado de Ventas",
    email,
    role,
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
      const role = credentials.role ?? "sales_delegate";
      const fallbackEmail =
        role === "regional_manager" ? "regional@inibsa.local" : "delegado@inibsa.local";
      const nextUser = createMockUser(credentials.email.trim() || fallbackEmail, role);
      saveSession(nextUser);
      return nextUser;
    },
    [saveSession],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      const role = credentials.role ?? "sales_delegate";
      const fallbackEmail =
        role === "regional_manager" ? "regional@inibsa.local" : "delegado@inibsa.local";
      const nextUser = createMockUser(credentials.email.trim() || fallbackEmail, role);
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
