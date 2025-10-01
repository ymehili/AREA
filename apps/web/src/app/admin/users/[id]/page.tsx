import { Suspense } from "react";
import UserDetailContent from "./UserDetailContent";
import AppShell from "@/components/app-shell";
import { cn, headingClasses } from "@/lib/utils";

export default function AdminUserDetailPage({ params }: { params: { id: string } }) {
  return (
    <AppShell>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
        <div>
          <h1 className={cn(headingClasses(1), "text-foreground")}>User Detail</h1>
          <p className="text-muted-foreground mt-1">
            View and manage user account details
          </p>
        </div>
      </div>

      <Suspense fallback={
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      }>
        <UserDetailContent userId={params.id} />
      </Suspense>
    </AppShell>
  );
}