import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import ca from "../locales/ca.json";
import en from "../locales/en.json";
import es from "../locales/es.json";

export type Language = "ca" | "es" | "en";
type Translations = typeof ca;

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (path: string, params?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const translations: Record<Language, Translations> = { ca, es, en };

function isLanguage(value: string | null): value is Language {
  return value === "ca" || value === "es" || value === "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem("app_lang");
    return isLanguage(saved) ? saved : "ca";
  });

  useEffect(() => {
    localStorage.setItem("app_lang", language);
    document.documentElement.lang = language;
  }, [language]);

  const t = (path: string, params?: Record<string, string | number>): string => {
    const keys = path.split(".");
    let current: any = translations[language];

    for (const key of keys) {
      if (current[key] === undefined) return path;
      current = current[key];
    }

    if (typeof current !== "string") return path;

    let result = current;
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        result = result.replace(`{{${key}}}`, String(value));
      });
    }

    return result;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useTranslation must be used within a LanguageProvider");
  }
  return context;
}
