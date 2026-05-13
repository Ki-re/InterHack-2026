import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Database,
  Github,
  GitBranch,
  LineChart,
  Network,
  Trophy,
} from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import { useAuth } from "@/auth/auth-context";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import inibsaLogo from "@/assets/logo.png";

const tech = ["React", "Vite", "TypeScript", "Tailwind", "shadcn/ui", "FastAPI", "Docker", "PyTorch", "Gemini", "ElevenLabs", "AssemblyAI", "SQLite"];

const team = [
  { key: "erik", name: "Erik Batiste", handle: "Ki-re", url: "https://github.com/Ki-re", avatar: "https://github.com/Ki-re.png" },
  { key: "ernest", name: "Ernest Rull", handle: "Yearsuck", url: "https://github.com/Yearsuck/Yearsuck", avatar: "https://github.com/Yearsuck.png" },
  { key: "alvaro", name: "Alvaro Saenz-Torre", handle: "Alvaroost8", url: "https://github.com/Alvaroost8", avatar: "https://github.com/Alvaroost8.png" },
] as const;

export function Landing() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const destination = user?.role === "regional_manager" ? "/regional-dashboard" : user ? "/dashboard" : "/login";

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="h-14 border-b bg-white/95">
        <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-6">
          <img src={inibsaLogo} alt="INIBSA" className="h-7 w-auto" />
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Button variant="outline" size="sm" onClick={() => navigate("/login")}>
              {t("landing.nav.login")}
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-[1440px] gap-4 px-4 py-4 sm:px-6 xl:h-[calc(100vh-3.5rem)] xl:overflow-hidden xl:grid-cols-[1.05fr_1.1fr_0.9fr]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-4 xl:min-h-0"
        >
          <div className="flex flex-col rounded-lg border bg-white p-6 shadow-sm xl:grow xl:min-h-0">
            <div className="xl:grow">
              <h1 className="text-5xl font-semibold leading-tight tracking-normal text-slate-950 2xl:text-6xl">
                {t("landing.hero.title")}
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600 2xl:text-base 2xl:leading-7">
                {t("landing.hero.description")}
              </p>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 2xl:text-sm">
                <Trophy className="size-3.5 2xl:size-4" aria-hidden="true" />
                {t("landing.hero.award_inibsa")}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 2xl:text-sm">
                <Trophy className="size-3.5 2xl:size-4" aria-hidden="true" />
                Best Use of ElevenLabs — MLH
              </span>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button className="h-11 px-5" onClick={() => navigate(destination)}>
                {t("landing.hero.cta")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Button>
              <a
                href="https://github.com/Ki-re/InterHack-2026/"
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-11 items-center gap-2 rounded-md border border-slate-200 bg-white px-5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50"
              >
                <Github className="size-4" aria-hidden="true" />
                GitHub
              </a>
            </div>
          </div>

          <Panel className="xl:grow xl:min-h-0">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-blue-700 2xl:text-base">
              <BarChart3 className="size-4" aria-hidden="true" />
              {t("landing.snapshot.title")}
            </div>
            <p className="text-sm leading-6 text-slate-600 2xl:text-base 2xl:leading-7">
              {t("landing.snapshot.description")}
            </p>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <Metric label={t("landing.snapshot.clinics")} value="6k" />
              <Metric label={t("landing.snapshot.alerts")} value="600" />
              <Metric label={t("landing.snapshot.frequency")} value={t("landing.snapshot.weekly")} />
            </div>
          </Panel>

          <Panel className="xl:grow xl:min-h-0 xl:overflow-hidden">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 2xl:text-sm">{t("landing.problem.eyebrow")}</p>
            <h2 className="mt-1 text-lg font-semibold 2xl:text-xl">{t("landing.problem.title")}</h2>
            <p className="mt-2 text-xs leading-5 text-slate-600 xl:grow 2xl:text-sm 2xl:leading-6">{t("landing.problem.description")}</p>
          </Panel>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.06 }}
          className="flex flex-col gap-4 xl:min-h-0"
        >
          <Panel className="p-3 xl:grow xl:min-h-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 2xl:text-sm">{t("landing.models.eyebrow")}</p>
            <h2 className="mt-1 text-lg font-semibold leading-tight 2xl:text-xl">{t("landing.models.title")}</h2>
            <div className="mt-3 grid gap-2 xl:grow xl:min-h-0 xl:auto-rows-fr">
              <ModelRow icon={<BrainCircuit />} title={t("landing.models.repurchase.title")} target="vuelve_a_comprar" text={t("landing.models.repurchase.description")} />
              <ModelRow icon={<LineChart />} title={t("landing.models.days.title")} target="dias_hasta_proxima_compra" text={t("landing.models.days.description")} />
              <ModelRow icon={<Network />} title={t("landing.models.potential.title")} target="target_potencial_cliente" text={t("landing.models.potential.description")} />
            </div>
          </Panel>

          <Panel className="xl:grow xl:min-h-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 2xl:text-sm">{t("landing.tech.eyebrow")}</p>
            <div className="mt-3 flex flex-wrap gap-2 xl:grow xl:content-start">
              {tech.map((item) => (
                <span key={item} className="rounded-md border bg-slate-50 px-2.5 py-1.5 text-xs font-semibold text-slate-700 2xl:text-sm">
                  {item}
                </span>
              ))}
            </div>
          </Panel>

          <div className="grid grid-cols-2 gap-3 xl:grow xl:min-h-0 xl:grid-rows-[1fr]">
            <InfoCard icon={<Database />} title={t("landing.data.title")} text={t("landing.data.description")} />
            <InfoCard icon={<GitBranch />} title={t("landing.pipeline.title")} text={t("landing.pipeline.description")} />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          className="flex flex-col gap-4 xl:min-h-0"
        >
          <Panel className="p-3 xl:grow xl:min-h-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 2xl:text-sm">{t("landing.team.eyebrow")}</p>
            <h2 className="mt-1 text-lg font-semibold leading-tight 2xl:text-xl">{t("landing.team.title")}</h2>
            <div className="mt-3 grid gap-2 xl:grow xl:min-h-0 xl:auto-rows-fr">
              {team.map((member) => (
                <a
                  key={member.key}
                  href={member.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex flex-col rounded-lg border bg-slate-50 p-3 transition-colors hover:bg-white"
                >
                  <div className="flex items-center gap-3">
                    <img src={member.avatar} alt={member.name} className="size-18 rounded-full border bg-white 2xl:size-20" />
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold 2xl:text-base">{member.name}</h3>
                      <p className="text-xs text-slate-500 2xl:text-sm">@{member.handle}</p>
                    </div>
                  </div>
                  <p className="mt-1.5 text-xs font-semibold text-blue-700 2xl:text-sm">{t(`landing.team.members.${member.key}.role`)}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-600 xl:grow 2xl:text-sm 2xl:leading-6">
                    {t(`landing.team.members.${member.key}.description`)}
                  </p>
                </a>
              ))}
            </div>
          </Panel>

          <div className="rounded-lg border bg-white px-4 py-3 text-xs leading-5 text-slate-500 shadow-sm xl:grow xl:min-h-0 2xl:text-sm 2xl:leading-6">
            {t("landing.footer.event")}
          </div>
        </motion.div>
      </section>
    </main>
  );
}

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex flex-col rounded-lg border bg-white p-4 shadow-sm ${className}`}>{children}</div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 2xl:text-xs">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-950 2xl:text-2xl">{value}</p>
    </div>
  );
}

function InfoCard({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <Panel>
      <div className="mb-2 flex size-8 items-center justify-center rounded-md bg-blue-50 text-blue-700">{icon}</div>
      <h3 className="text-sm font-semibold 2xl:text-base">{title}</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600 xl:grow 2xl:text-sm 2xl:leading-6">{text}</p>
    </Panel>
  );
}

function ModelRow({ icon, title, target, text }: { icon: ReactNode; title: string; target: string; text: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-slate-50 p-2.5 sm:flex-row">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-green-50 text-green-700">{icon}</div>
      <div className="flex min-w-0 flex-col xl:grow">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-xs font-semibold text-slate-950 2xl:text-sm">{title}</h3>
          <span className="font-mono text-[10px] text-green-700 2xl:text-xs">{target}</span>
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-600 xl:grow 2xl:text-sm 2xl:leading-6">{text}</p>
      </div>
    </div>
  );
}
