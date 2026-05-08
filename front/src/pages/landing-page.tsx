import { type FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Hero from "@/components/ui/animated-shader-hero";
import { useAuth } from "@/auth/auth-context";

type AuthMode = "login" | "register";

export function LandingPage() {
  const [mode, setMode] = useState<AuthMode | null>(null);
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

  function selectMode(nextMode: AuthMode) {
    setError(null);
    setMode(nextMode);
  }

  return (
    <main className="min-h-screen bg-black text-white">
      <Hero
        trustBadge={{
          text: "Secure workspace access",
        }}
        headline={{
          line1: "InterHack",
          line2: "Workspace",
        }}
        subtitle="Register or log in to continue from a focused full-stack dashboard built for fast-moving hackathon teams."
        buttons={{
          primary: {
            text: "Register",
            onClick: () => selectMode("register"),
          },
          secondary: {
            text: "Login",
            onClick: () => selectMode("login"),
          },
        }}
      >
        {mode ? (
          <div className="pointer-events-auto absolute inset-x-4 bottom-4 mx-auto max-w-md sm:bottom-8 lg:bottom-auto lg:left-auto lg:right-8 lg:top-1/2 lg:mx-0 lg:-translate-y-1/2">
            <Card className="max-h-[calc(100vh-2rem)] overflow-y-auto border-white/15 bg-white/95 text-foreground shadow-2xl shadow-black/40 backdrop-blur">
              <CardHeader>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div className="flex size-9 items-center justify-center rounded-md bg-orange-100 text-orange-700">
                    <ShieldCheck className="size-5" aria-hidden="true" />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    type="button"
                    onClick={() => {
                      setError(null);
                      setMode(null);
                    }}
                  >
                    <ArrowLeft className="size-4" aria-hidden="true" />
                    Back
                  </Button>
                </div>
                <CardTitle>{isRegistering ? "Create an account" : "Welcome back"}</CardTitle>
                <CardDescription>
                  {isRegistering
                    ? "Use an email and password to start your session."
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
                    onClick={() => selectMode(isRegistering ? "login" : "register")}
                  >
                    {isRegistering ? "Sign in" : "Register"}
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </Hero>
    </main>
  );
}
