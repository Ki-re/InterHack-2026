import { type FormEvent, useState } from "react";
import { ArrowRight, LockKeyhole, Mail } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import { useAuth } from "@/auth/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/contexts/LanguageContext";
import inibsaLogo from "@/assets/logo.png";
import inibsaIcon from "@/assets/icon.png";

export function Login() {
  const { login } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    try {
      if (!email.trim() || !password.trim()) {
        throw new Error(t("login.error_required"));
      }

      await login({ email, password });
      navigate("/dashboard", { replace: true });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : t("login.error_failed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 text-foreground">
      <div className="mx-auto grid min-h-screen w-full max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[1fr_430px] lg:items-center lg:px-6">
        <motion.section 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="max-w-2xl"
        >
          <div className="inline-flex items-center gap-2 rounded-full border bg-white px-3 py-1 text-sm font-medium text-primary shadow-sm">
              <img src={inibsaIcon} alt="" className="size-4" aria-hidden="true" />
              {t("app.challenge")}
            </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl">
            {t("login.title")}
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
            {t("login.description")}
          </p>

          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
            <Signal label={t("login.signals.churn")} value="82%" tone="risk" />
            <Signal label={t("login.signals.buy")} value="74%" tone="success" />
            <Signal label={t("login.signals.clients")} value="6" tone="neutral" />
          </div>
        </motion.section>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="rounded-lg border-slate-200 shadow-lg shadow-slate-200/80">
            <CardHeader>
              <div className="mb-3">
                <img src={inibsaLogo} alt="INIBSA" className="h-8 w-auto" />
              </div>
              <CardTitle className="text-xl">{t("login.role")}</CardTitle>
              <CardDescription>{t("login.mock_login")}</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <label className="block space-y-2">
                  <span className="text-sm font-medium">{t("login.email")}</span>
                  <span className="relative block">
                    <Mail
                      className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <input
                      className="h-10 w-full rounded-md border bg-background px-9 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
                      defaultValue="delegado@inibsa.local"
                      name="email"
                      type="email"
                      autoComplete="email"
                    />
                  </span>
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium">{t("login.password")}</span>
                  <span className="relative block">
                    <LockKeyhole
                      className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <input
                      className="h-10 w-full rounded-md border bg-background px-9 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
                      defaultValue="demo1234"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                    />
                  </span>
                </label>

                {error ? (
                  <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {error}
                  </p>
                ) : null}

                <Button className="w-full" type="submit" disabled={isSubmitting}>
                  {isSubmitting ? t("login.entering") : t("login.submit")}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </main>
  );
}

function Signal({ label, tone, value }: { label: string; tone: "risk" | "success" | "neutral"; value: string }) {
  const toneClassName = {
    risk: "text-red-700",
    success: "text-green-700",
    neutral: "text-primary",
  }[tone];

  return (
    <div className="rounded-lg border bg-white px-4 py-3 shadow-sm transition-transform hover:scale-[1.02]">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${toneClassName}`}>{value}</p>
    </div>
  );
}
