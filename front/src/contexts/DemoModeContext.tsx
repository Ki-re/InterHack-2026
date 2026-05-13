import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useTranslation } from "@/contexts/LanguageContext";

type DemoModeContextValue = {
  isDemoMode: boolean;
  showDemoNotice: (message?: string) => void;
};

const STORAGE_KEY = "demo_mode";
const DemoModeContext = createContext<DemoModeContextValue | undefined>(undefined);

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [notice, setNotice] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const showDemoNotice = useCallback(
    (message?: string) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      setNotice(message ?? t("demo.default_notice"));
      timeoutRef.current = setTimeout(() => setNotice(null), 4200);
    },
    [t],
  );

  const value = useMemo(
    () => ({
      isDemoMode: true,
      showDemoNotice,
    }),
    [showDemoNotice],
  );

  return (
    <DemoModeContext.Provider value={value}>
      {children}
      {notice ? (
        <div
          role="status"
          className="fixed bottom-4 right-4 z-[70] max-w-sm rounded-lg border border-blue-200 bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-xl shadow-slate-300/40"
        >
          <div className="font-semibold text-slate-950">{t("demo.badge")}</div>
          <div>{notice}</div>
        </div>
      ) : null}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  const context = useContext(DemoModeContext);
  if (context === undefined) {
    throw new Error("useDemoMode must be used within a DemoModeProvider.");
  }
  return context;
}
