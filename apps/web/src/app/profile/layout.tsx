"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import AppShell from "@/components/app-shell";
import { cn, headingClasses } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const TABS = [
  { href: "/profile", label: "Profile" },
  { href: "/profile/activity-log", label: "Activity Log" },
  { href: "/profile/automation-history", label: "Automation History" },
];

export default function ProfileLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className={cn(headingClasses(1), "text-foreground")}>Account Management</h1>
          <p className="text-sm text-muted-foreground">
            Manage how you sign in and update the details associated with your account.
          </p>
        </div>
        <Separator />
        
        <div className="flex flex-col space-y-6 md:flex-row md:space-y-0 md:space-x-8">
          <div className="w-full md:w-1/4">
            <Card role="complementary" aria-labelledby="sidebar-heading">
              <div id="sidebar-heading" className="sr-only">Account Management Sections</div>
              <CardContent className="p-4">
                <nav aria-label="Account management navigation">
                  <ul className="flex flex-col space-y-2">
                    {TABS.map((tab) => (
                      <li key={tab.href}>
                        <Link
                          href={tab.href}
                          className={`px-3 py-2 text-sm rounded-md transition-colors ${
                            pathname === tab.href
                              ? "bg-foreground text-background"
                              : "hover:bg-muted"
                          }`}
                          aria-current={
                            pathname === tab.href
                              ? "page"
                              : undefined
                          }
                        >
                          {tab.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </nav>
              </CardContent>
            </Card>
          </div>
          
          <div className="w-full md:w-3/4">
            {children}
          </div>
        </div>
      </div>
    </AppShell>
  );
}