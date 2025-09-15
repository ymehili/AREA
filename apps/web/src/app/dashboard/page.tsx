"use client";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useState } from "react";

type Area = {
  id: string;
  name: string;
  trigger: string;
  action: string;
  enabled: boolean;
};

const mockAreas: Area[] = [
  {
    id: "1",
    name: "Save Gmail invoices to Drive",
    trigger: "Gmail: New Email w/ 'Invoice'",
    action: "Drive: Upload Attachment",
    enabled: true,
  },
  {
    id: "2",
    name: "Notify Slack on new PR",
    trigger: "GitHub: New Pull Request",
    action: "Slack: Send Message",
    enabled: false,
  },
];

export default function DashboardPage() {
  const [areas, setAreas] = useState<Area[]>(mockAreas);

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button onClick={() => (window.location.href = "/wizard")}>Create AREA</Button>
      </div>
      {areas.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Get started</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">You have no AREAs yet.</p>
            <Button onClick={() => (window.location.href = "/wizard")}>Create your first AREA</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
          {areas.map((area) => (
            <Card key={area.id}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-base font-medium">{area.name}</CardTitle>
                <Badge variant={area.enabled ? "default" : "secondary"}>
                  {area.enabled ? "Enabled" : "Disabled"}
                </Badge>
              </CardHeader>
              <CardContent className="flex items-center justify-between gap-2">
                <div className="text-sm text-muted-foreground">
                  <div>When: {area.trigger}</div>
                  <div>Then: {area.action}</div>
                </div>
                <Switch
                  checked={area.enabled}
                  onCheckedChange={(v) =>
                    setAreas((prev) => prev.map((a) => (a.id === area.id ? { ...a, enabled: v } : a)))
                  }
                />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}

