import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  getCurrentUser,
  login as loginRequest,
  register as registerRequest,
  type AuthCredentials,
  type AuthResponse,
  type AuthUser,
} from "@/api/auth";

const STORAGE_KEY = "interhack.accessToken";

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (credentials: AuthCredentials) => Promise<AuthUser>;
  register: (credentials: AuthCredentials) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(() => Boolean(token));

  const clearSession = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    setIsLoading(false);
  }, []);

  const saveSession = useCallback((response: AuthResponse) => {
    localStorage.setItem(STORAGE_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      setUser(null);
      setIsLoading(false);
      return () => {
        isCurrent = false;
      };
    }

    setIsLoading(true);
    getCurrentUser(token)
      .then((currentUser) => {
        if (isCurrent) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (isCurrent) {
          clearSession();
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [clearSession, token]);

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const response = await loginRequest(credentials);
      saveSession(response);
      return response.user;
    },
    [saveSession],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      const response = await registerRequest(credentials);
      saveSession(response);
      return response.user;
    },
    [saveSession],
  );

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      login,
      register,
      logout: clearSession,
    }),
    [clearSession, isLoading, login, register, token, user],
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
