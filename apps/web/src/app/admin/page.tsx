"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn, headingClasses } from "@/lib/utils";
import { UnauthorizedError, fetchAdminUsers, deleteAdminUser, createAdminUser, CreateUserPayload } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";

type AdminUser = {
  id: string;
  email: string;
  full_name: string | null;
  is_confirmed: boolean;
  is_admin: boolean;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
};

// Type definition that matches the backend response
type PaginatedUsers = {
  items: AdminUser[];
  total: number;
  page: number;
  limit: number;
  pages: number;
};

export default function AdminPage() {
  const auth = useRequireAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<{id: string, email: string} | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserIsAdmin, setNewUserIsAdmin] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);

  const loadUsers = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await fetchAdminUsers(
        auth.token,
        (currentPage - 1) * 10, // skip
        10, // limit
        search
      );
      setUsers(data.items);
      setTotalPages(data.pages);
      setTotalUsers(data.total);
      setError(null);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : "Unable to load users.";
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [auth, currentPage, search]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  // Handle search submission when Enter is pressed
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      setCurrentPage(1); // Reset to first page when searching
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete || !auth.token) return;

    try {
      await deleteAdminUser(auth.token, userToDelete.id);
      toast.success(`User ${userToDelete.email} has been deleted successfully`);
      setIsDeleteDialogOpen(false);
      setUserToDelete(null);
      void loadUsers(); // Refresh the user list
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : `Failed to delete user ${userToDelete.email}.`;
      toast.error(message);
    }
  };

  const handleCreateUser = async () => {
    if (!auth.token || !newUserEmail || !newUserPassword) return;

    setCreateLoading(true);
    try {
      const payload: CreateUserPayload = {
        email: newUserEmail,
        password: newUserPassword
      };
      
      await createAdminUser(auth.token, payload, newUserIsAdmin);
      toast.success(`User ${newUserEmail} has been created successfully`);
      setIsCreateDialogOpen(false);
      setNewUserEmail("");
      setNewUserPassword("");
      setNewUserIsAdmin(false);
      void loadUsers(); // Refresh the user list
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        auth.logout();
        toast.error("Session expired. Please sign in again.");
        return;
      }
      const message = err instanceof Error ? err.message : `Failed to create user.`;
      toast.error(message);
    } finally {
      setCreateLoading(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-between mb-6">
          <h1 className={cn(headingClasses(1), "text-foreground")}>User Management</h1>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="flex items-center justify-between mb-6">
          <h1 className={cn(headingClasses(1), "text-foreground")}>User Management</h1>
        </div>
        <div className="flex justify-center items-center h-64">
          <div className="text-destructive text-center">
            <p className="font-semibold">Error loading users</p>
            <p>{error}</p>
            <Button onClick={() => void loadUsers()} className="mt-4">
              Retry
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className={cn(headingClasses(1), "text-foreground")}>User Management</h1>
      </div>

      <Card className="mb-6">
        <CardContent className="p-4 mt-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                type="text"
                placeholder="Search users by email..."
                value={search}
                onChange={handleSearch}
                onKeyDown={handleSearchKeyDown}
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="mb-6 text-sm text-muted-foreground">
        Showing {users.length} of {totalUsers} users
      </div>

      <div className="flex justify-end mb-4">
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create User</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Create New User</DialogTitle>
              <DialogDescription>
                Enter the details for the new user account.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="email" className="text-right">
                  Email
                </Label>
                <Input
                  id="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="password" className="text-right">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  className="col-span-3"
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="admin" className="text-right">
                  Admin User
                </Label>
                <Switch
                  id="admin"
                  checked={newUserIsAdmin}
                  onCheckedChange={setNewUserIsAdmin}
                />
              </div>
            </div>
            <DialogFooter>
              <Button 
                type="submit" 
                onClick={handleCreateUser}
                disabled={createLoading}
              >
                {createLoading ? 'Creating...' : 'Create User'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {users.length === 0 ? (
        <Card className="p-6">
          <CardHeader className="p-0 mb-4">
            <CardTitle className={cn(headingClasses(3), "text-foreground")}>No users found</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <p className="text-sm text-muted-foreground">
              {search ? "No users match your search criteria." : "There are no users in the system yet."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {users.map((user) => (
            <Card key={user.id} className="p-4">
              <CardHeader className="p-0 mb-4">
                <div className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-lg font-medium text-foreground">{user.email}</CardTitle>
                  <div className="flex space-x-2">
                    <Badge variant={user.is_confirmed ? "default" : "secondary"}>
                      {user.is_confirmed ? "Confirmed" : "Unconfirmed"}
                    </Badge>
                    {user.is_admin && (
                      <Badge variant="outline">
                        Admin
                      </Badge>
                    )}
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => {
                        setUserToDelete({id: user.id, email: user.email});
                        setIsDeleteDialogOpen(true);
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="text-sm text-muted-foreground mb-2">
                  <div>ID: {user.id}</div>
                  <div>Created: {new Date(user.created_at).toLocaleDateString()}</div>
                  {user.full_name && <div>Name: {user.full_name}</div>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Delete</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the user <strong>{userToDelete?.email}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setIsDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteUser}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </AppShell>
  );
}