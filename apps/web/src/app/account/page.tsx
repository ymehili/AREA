"use client";
import AppShell from "@/components/app-shell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

export default function AccountPage() {
  return (
    <AppShell>
      <h1 className="text-2xl font-semibold mb-4">Account Management</h1>
      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="history">Automation History</TabsTrigger>
          <TabsTrigger value="activity">Activity Log</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-4">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <div className="grid gap-2 max-w-md">
                <Label htmlFor="name">Name</Label>
                <Input id="name" defaultValue="Jane Doe" />
              </div>
              <div className="grid gap-2 max-w-md">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" defaultValue="jane@example.com" />
              </div>
              <Button className="w-fit">Save</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardContent className="pt-6 text-sm text-muted-foreground">
              Recent runs of your AREAs will appear here. (Mock)
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <Card>
            <CardContent className="pt-6 text-sm text-muted-foreground">
              Activity across your account will appear here. (Mock)
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}

