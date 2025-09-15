"use client";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

type Service = { id: string; name: string; connected: boolean };

const initial: Service[] = [
  { id: "google", name: "Google Drive", connected: true },
  { id: "gmail", name: "Gmail", connected: true },
  { id: "slack", name: "Slack", connected: false },
  { id: "github", name: "GitHub", connected: false },
];

export default function ConnectionsPage() {
  const [services, setServices] = useState<Service[]>(initial);

  const toggle = (id: string, state: boolean) => {
    setServices((prev) => prev.map((s) => (s.id === id ? { ...s, connected: state } : s)));
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Service Connection Hub</h1>
      </div>
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {services.map((s) => (
          <Card key={s.id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">{s.name}</CardTitle>
              <Badge variant={s.connected ? "default" : "secondary"}>
                {s.connected ? "Connected" : "Not connected"}
              </Badge>
            </CardHeader>
            <CardContent className="flex gap-2 justify-end">
              {s.connected ? (
                <Button variant="outline" onClick={() => toggle(s.id, false)}>
                  Disconnect
                </Button>
              ) : (
                <Button onClick={() => toggle(s.id, true)}>Connect</Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}

