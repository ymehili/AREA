"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/hooks/use-auth";
import { getUserDetail, confirmUserEmail, suspendUserAccount, deleteUserAccount } from "@/lib/api";
import UserDetailsCard from "./UserDetailsCard";
import UserConnectionsCard from "./UserConnectionsCard";
import UserAreasCard from "./UserAreasCard";

// Define the user detail type based on the backend schema
type ServiceConnection = {
  id: string;
  service_name: string;
  created_at: string;
};

type Area = {
  id: string;
  name: string;
  trigger_service: string;
  reaction_service: string;
  enabled: boolean;
  created_at: string;
};

type UserDetail = {
  id: string;
  email: string;
  full_name: string | null;
  is_confirmed: boolean;
  is_admin: boolean;
  is_suspended: boolean;
  created_at: string;
  confirmed_at: string | null;
  service_connections: ServiceConnection[];
  areas: Area[];
};

export default function UserDetailContent({ userId }: { userId: string }) {
  const auth = useRequireAuth();
  const [user, setUser] = useState<UserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suspendReason, setSuspendReason] = useState("");
  const [deleteReason, setDeleteReason] = useState("");

  // Load user details when component mounts
  useEffect(() => {
    if (!auth.token || !userId) return;

    const loadUserDetail = async () => {
      try {
        const userData = await getUserDetail(auth.token!, userId);
        setUser(userData);
        setError(null);
      } catch (err) {
        if (err instanceof Error && err.message.includes("401")) {
          auth.logout();
          toast.error("Session expired. Please sign in again.");
          return;
        }
        const message = err instanceof Error ? err.message : "Unable to load user details.";
        setError(message);
        toast.error(message);
      } finally {
        setLoading(false);
      }
    };

    void loadUserDetail();
  }, [auth, userId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-destructive text-center">
          <p className="font-semibold">Error loading user details</p>
          <p>{error}</p>
          <Button onClick={() => window.location.reload()} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-destructive text-center">
          <p>User not found</p>
        </div>
      </div>
    );
  }

  // Handle confirming user email
  const handleConfirmEmail = async () => {
    if (!auth.token) {
      toast.error("Authentication token is missing");
      return;
    }

    try {
      const response = await confirmUserEmail(auth.token, user.id);
      setUser(prev => 
        prev ? { 
          ...prev, 
          is_confirmed: response.is_confirmed !== undefined ? response.is_confirmed : prev.is_confirmed 
        } : null
      );
      toast.success(response.message);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to confirm user email";
      toast.error(message);
    }
  };

  // Handle suspending user account
  const handleSuspendAccount = async () => {
    if (!auth.token) {
      toast.error("Authentication token is missing");
      return;
    }

    try {
      const response = await suspendUserAccount(auth.token, user.id);
      setUser(prev => 
        prev ? { 
          ...prev, 
          is_suspended: response.is_suspended !== undefined ? response.is_suspended : prev.is_suspended 
        } : null
      );
      toast.success(response.message);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to suspend user account";
      toast.error(message);
    }
  };

  // Handle deleting user account
  const handleDeleteAccount = async () => {
    if (!auth.token) {
      toast.error("Authentication token is missing");
      return;
    }

    try {
      await deleteUserAccount(auth.token, user.id);
      toast.success("User account has been deleted");
      // In a real implementation, you might want to navigate away after deletion
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to delete user account";
      toast.error(message);
    }
  };

  return (
    <div className="space-y-6">
      <UserDetailsCard user={user} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <UserConnectionsCard connections={user.service_connections} />
        <UserAreasCard areas={user.areas} />
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap gap-3">
            {!user.is_confirmed && (
              <Button onClick={handleConfirmEmail}>
                Confirm User Email
              </Button>
            )}
            
            {!user.is_suspended && (
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="destructive">Suspend Account</Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle>Suspend User Account</DialogTitle>
                    <DialogDescription>
                      This will temporarily disable the user&apos;s account. Provide a reason for the suspension.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <Input
                      placeholder="Reason for suspension..."
                      value={suspendReason}
                      onChange={(e) => setSuspendReason(e.target.value)}
                    />
                  </div>
                  <DialogFooter>
                    <Button
                      variant="secondary"
                      onClick={() => setSuspendReason("")}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => {
                        // For now, we'll just call handleSuspendAccount directly
                        // In the future, we could pass the reason to the backend
                        handleSuspendAccount();
                        setSuspendReason("");
                      }}
                    >
                      Suspend
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}

            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive">Delete Account</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Delete User Account</DialogTitle>
                  <DialogDescription>
                    This will permanently delete the user&apos;s account and all associated data. This action cannot be undone. Provide a reason for the deletion.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <Input
                    placeholder="Reason for deletion..."
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                  />
                </div>
                <DialogFooter>
                  <Button
                    variant="secondary"
                    onClick={() => setDeleteReason("")}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      handleDeleteAccount();
                      setDeleteReason("");
                    }}
                  >
                    Delete
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}