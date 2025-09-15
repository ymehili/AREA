"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    try {
      localStorage.removeItem("ar_auth");
    } catch {}
    router.push("/");
  };

  const NavLink = ({ href, label }: { href: string; label: string }) => {
    const active = pathname === href;
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
      <header className="sticky top-0 z-10 w-full border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 h-14 flex items-center gap-2 justify-between">
          <div className="flex items-center gap-2">
            <Link href="/dashboard" className="font-semibold">Action-Reaction</Link>
            <Separator orientation="vertical" className="h-6" />
            <nav className="hidden md:flex items-center gap-1">
              <NavLink href="/dashboard" label="Dashboard" />
              <NavLink href="/connections" label="Connections" />
              <NavLink href="/wizard" label="Create AREA" />
              <NavLink href="/account" label="Account" />
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => router.push("/wizard")}>Create AREA</Button>
            <Button size="sm" variant="ghost" onClick={logout}>Logout</Button>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6 flex-1">{children}</main>
    </div>
  );
}

