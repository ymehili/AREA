"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { useRequireAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { fetchProfile, UnauthorizedError } from "@/lib/api";


// Define navigation routes
const NAV_ROUTES = [
  { href: "/dashboard", label: "Dashboard", showInNav: true },
  { href: "/connections", label: "Connections", showInNav: true },
  { href: "/profile", label: "Account", showInNav: true },
  { href: "/history", label: "History", showInNav: true },
  { href: "/admin/users", label: "User Management", showInNav: true },  // Admin route
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
  const [isAdmin, setIsAdmin] = useState(false);

  // Fetch user profile when token is available
  useEffect(() => {
    if (auth.token) {
      const fetchUserProfile = async () => {
        try {
          const profile = await fetchProfile(auth.token!);
          setIsAdmin(profile.is_admin || false);
        } catch (error) {
          // If it's an UnauthorizedError (401), it means the token is invalid/expired
          if (error instanceof UnauthorizedError) {
            // Automatically log out the user
            auth.logout();
          } else {
            // For other errors, we assume the user is not an admin
            // Only log non-unauthorized errors to avoid console spam
            console.error("Error fetching user profile:", error);
            setIsAdmin(false);
          }
        }
      };

      fetchUserProfile();
    } else {
      // Reset admin status if there's no token
      setIsAdmin(false);
    }
  }, [auth.token]);

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

  // Filter navigation routes based on whether the user is an admin
  const filteredRoutes = NAV_ROUTES.filter(route => {
    // If the route is an admin route, only show it to admin users
    if (route.href.startsWith('/admin')) {
      return route.showInNav && isAdmin;
    }
    // Otherwise, show regular routes to all users
    return route.showInNav;
  });

  const breadcrumbs = getBreadcrumbs(pathname);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 w-full border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-border">
        <div className="container mx-auto px-4 h-16 flex items-center gap-6 justify-between">
          <div className="flex items-center gap-6">
            <Link 
              href="/dashboard" 
              className="font-heading font-normal text-xl tracking-[1px] uppercase text-foreground"
              aria-label="Action-Reaction Home"
            >
              Action-Reaction
            </Link>
            <Separator orientation="vertical" className="h-6 bg-border" />
            <nav className="hidden md:flex items-center gap-2" aria-label="Main navigation">
              {filteredRoutes.map(route => (
                <NavLink key={route.href} href={route.href} label={route.label} />
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <Button 
                size="sm" 
                variant="secondary"
                onClick={() => router.push("/admin/users")}
                aria-label="Admin dashboard"
              >
                Admin Panel
              </Button>
            )}
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
      
      <div className="container mx-auto px-4 py-6 flex-1">
        {/* Breadcrumb navigation */}
        {breadcrumbs.length > 1 && (
          <nav className="mb-6" aria-label="Breadcrumb">
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
