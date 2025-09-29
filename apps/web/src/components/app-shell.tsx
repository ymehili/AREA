"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";

import { useRequireAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = useRequireAuth();

  if (auth.initializing) {
    return (
      <div className="min-h-screen grid place-items-center bg-background">
        <span className="text-sm text-muted-foreground">Preparing your workspace…</span>
      </div>
    );
  }

  const handleLogout = () => {
    auth.logout();
  };

  const NavLink = ({ href, label }: { href: string; label: string }) => {
    const active = pathname === href || pathname.startsWith(`${href}/`);
    return (
      <Link
        href={href}
        className={`text-sm px-3 py-2 rounded-md transition-colors ${
          active ? "bg-foreground text-background" : "hover:bg-muted"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 w-full border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-border">
        <div className="container mx-auto px-4 h-16 flex items-center gap-4 justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="font-heading font-normal text-xl tracking-[1px] uppercase text-foreground">
              Action-Reaction
            </Link>
            <Separator orientation="vertical" className="h-6 bg-border" />
            <nav className="hidden md:flex items-center gap-2">
              <NavLink href="/dashboard" label="Dashboard" />
              <NavLink href="/connections" label="Connections" />
              <NavLink href="/profile" label="Account" />
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="default" onClick={() => router.push("/wizard")}>Create AREA</Button>
            <Button size="sm" variant="ghost" onClick={handleLogout} disabled={auth.loading} className="text-foreground border-border hover:bg-accent">
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8 flex-1">{children}</main>
    </div>
  );
}
