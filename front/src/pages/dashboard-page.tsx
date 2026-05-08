import { Activity, Box, Database, Server } from "lucide-react";

import { API_BASE_URL } from "@/api/client";
import { useAuth } from "@/auth/auth-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useHealth } from "@/hooks/use-health";

export function DashboardPage() {
  const health = useHealth();
  const { user } = useAuth();
  const apiStatus = health.data?.status ?? (health.isLoading ? "checking" : "offline");
  const isHealthy = health.data?.status === "ok";

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 border-b pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl space-y-2">
          <p className="text-sm font-medium text-accent">Hackathon workspace</p>
          <h1 className="text-3xl font-semibold text-foreground">Dashboard</h1>
          <p className="text-sm leading-6 text-muted-foreground">
            Signed in as {user?.email}. A lean React and FastAPI starter with Docker-first
            local development.
          </p>
        </div>
        <Button asChild>
          <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
            <Server className="size-4" aria-hidden="true" />
            Open API
          </a>
        </Button>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Backend</CardTitle>
              <Activity className={isHealthy ? "size-5 text-accent" : "size-5 text-destructive"} />
            </div>
            <CardDescription>FastAPI service status</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold capitalize">{apiStatus}</p>
            <p className="mt-2 text-sm text-muted-foreground">{API_BASE_URL}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Database</CardTitle>
              <Database className="size-5 text-primary" />
            </div>
            <CardDescription>SQLite with async SQLAlchemy</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">Ready</p>
            <p className="mt-2 text-sm text-muted-foreground">Alembic migration managed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Frontend</CardTitle>
              <Box className="size-5 text-accent" />
            </div>
            <CardDescription>Vite, React Router, Query</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">Live</p>
            <p className="mt-2 text-sm text-muted-foreground">Hot reload enabled</p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
