import { type FormEvent, useState } from "react";
import { ArrowRight, CheckCircle2, LockKeyhole, Mail, PanelsTopLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/auth/auth-context";

type AuthMode = "login" | "register";

export function LandingPage() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const isRegistering = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");

    try {
      if (isRegistering) {
        await register({ email, password });
      } else {
        await login({ email, password });
      }
      navigate("/dashboard", { replace: true });
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Authentication failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="space-y-8">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <PanelsTopLeft className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold">InterHack</p>
              <p className="text-xs text-muted-foreground">Hackathon workspace</p>
            </div>
          </div>

          <div className="max-w-2xl space-y-4">
            <p className="text-sm font-medium text-accent">React + FastAPI starter</p>
            <h1 className="text-4xl font-semibold text-foreground sm:text-5xl">
              Build from a clean dashboard.
            </h1>
            <p className="max-w-xl text-base leading-7 text-muted-foreground">
              Register once, sign in, and land directly in the workspace your team can extend.
            </p>
          </div>

          <div className="grid max-w-2xl gap-3 sm:grid-cols-3">
            {["Async API", "SQLite ready", "Hot reload"].map((item) => (
              <div key={item} className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
                <CheckCircle2 className="size-4 text-accent" aria-hidden="true" />
                <span className="text-sm font-medium">{item}</span>
              </div>
            ))}
          </div>
        </section>

        <Card className="w-full max-w-md justify-self-center">
          <CardHeader>
            <CardTitle>{isRegistering ? "Create an account" : "Welcome back"}</CardTitle>
            <CardDescription>
              {isRegistering
                ? "Use an email and password to start a workspace session."
                : "Sign in to continue to your dashboard."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <label className="block space-y-2">
                <span className="text-sm font-medium">Email</span>
                <span className="relative block">
                  <Mail
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <input
                    className="h-10 w-full rounded-md border bg-background px-9 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    required
                  />
                </span>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium">Password</span>
                <span className="relative block">
                  <LockKeyhole
                    className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <input
                    className="h-10 w-full rounded-md border bg-background px-9 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
                    name="password"
                    type="password"
                    autoComplete={isRegistering ? "new-password" : "current-password"}
                    minLength={8}
                    placeholder="Minimum 8 characters"
                    required
                  />
                </span>
              </label>

              {error ? (
                <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              ) : null}

              <Button className="w-full" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Please wait" : isRegistering ? "Create account" : "Sign in"}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Button>
            </form>

            <div className="mt-5 border-t pt-5 text-center text-sm text-muted-foreground">
              {isRegistering ? "Already have an account?" : "Need an account?"}{" "}
              <button
                className="font-medium text-primary hover:underline"
                type="button"
                onClick={() => {
                  setError(null);
                  setMode(isRegistering ? "login" : "register");
                }}
              >
                {isRegistering ? "Sign in" : "Register"}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
