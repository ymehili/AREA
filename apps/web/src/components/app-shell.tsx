"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";

import { useRequireAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn, headingClasses } from "@/lib/utils";

// Define navigation routes
const NAV_ROUTES = [
  { href: "/dashboard", label: "Dashboard", showInNav: true },
  { href: "/connections", label: "Connections", showInNav: true },
  { href: "/profile", label: "Account", showInNav: true },
  { href: "/history", label: "History", showInNav: true }, // Post-MVP as per specs
];

type Breadcrumb = {
  label: string;
  href?: string;
};

// Function to generate breadcrumbs based on current path
const getBreadcrumbs = (pathname: string): Breadcrumb[] => {
  const segments = pathname.split('/').filter(Boolean);
  
  if (segments.length === 0) return [{ label: "Dashboard", href: "/dashboard" }];
  
  const breadcrumbs: Breadcrumb[] = [{ label: "Dashboard", href: "/dashboard" }];
  
  // If we're in profile section, add account first
  if (segments[0] === 'profile') {
    breadcrumbs.push({ label: "Account", href: "/profile" });
    
    if (segments.length > 1) {
      const subPage = segments[1];
      if (subPage === 'activity-log') {
        breadcrumbs.push({ label: "Activity Log" });
      } else if (subPage === 'automation-history') {
        breadcrumbs.push({ label: "Automation History" });
      }
    }
  } else if (segments[0] === 'dashboard' && segments[1]) {
    breadcrumbs.push({ label: "My AREAs", href: "/dashboard" });
    if (segments[2] === 'edit') {
      breadcrumbs.push({ label: segments[1], href: `/dashboard/${segments[1]}` });
      breadcrumbs.push({ label: "Edit" });
    } else {
      breadcrumbs.push({ label: segments[1] });
    }
  }
  
  return breadcrumbs;
};

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
        aria-current={active ? "page" : undefined}
      >
        {label}
      </Link>
    );
  };

  const breadcrumbs = getBreadcrumbs(pathname);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 w-full border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-border">
        <div className="container mx-auto px-4 h-16 flex items-center gap-4 justify-between">
          <div className="flex items-center gap-4">
            <Link 
              href="/dashboard" 
              className="font-heading font-normal text-xl tracking-[1px] uppercase text-foreground"
              aria-label="Action-Reaction Home"
            >
              Action-Reaction
            </Link>
            <Separator orientation="vertical" className="h-6 bg-border" />
            <nav className="hidden md:flex items-center gap-2" aria-label="Main navigation">
              {NAV_ROUTES.filter(route => route.showInNav).map(route => (
                <NavLink key={route.href} href={route.href} label={route.label} />
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              size="sm" 
              variant="default" 
              onClick={() => router.push("/wizard")}
              aria-label="Create new AREA"
            >
              Create AREA
            </Button>
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={handleLogout} 
              disabled={auth.loading} 
              className="text-foreground border-border hover:bg-accent"
              aria-label="Logout"
            >
              Logout
            </Button>
          </div>
        </div>
      </header>
      
      <div className="container mx-auto px-4 py-4 flex-1">
        {/* Breadcrumb navigation */}
        {breadcrumbs.length > 1 && (
          <nav className="mb-4" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-2 text-sm text-muted-foreground">
              {breadcrumbs.map((crumb, index) => (
                <li key={index} className="flex items-center">
                  {crumb.href ? (
                    <Link href={crumb.href} className="hover:text-foreground transition-colors">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-foreground" aria-current="page">
                      {crumb.label}
                    </span>
                  )}
                  {index < breadcrumbs.length - 1 && (
                    <span className="mx-2 text-muted-foreground" aria-hidden="true">
                      /
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}
        
        <main>{children}</main>
      </div>
    </div>
  );
}
