import { Button } from "@/components/ui/button";
import { useTranslation, type Language } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";

const LANGUAGES: { code: Language; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "ca", label: "CA" },
  { code: "es", label: "ES" },
];

type LanguageSwitcherProps = {
  className?: string;
};

export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const { language, setLanguage } = useTranslation();

  return (
    <div className={cn("flex items-center gap-1 rounded-md border bg-background p-1", className)}>
      {LANGUAGES.map((item) => (
        <Button
          key={item.code}
          variant={language === item.code ? "secondary" : "ghost"}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => setLanguage(item.code)}
          type="button"
        >
          {item.label}
        </Button>
      ))}
    </div>
  );
}
