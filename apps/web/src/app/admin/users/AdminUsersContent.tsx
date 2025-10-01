"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import CreateUserForm from "@/components/admin/CreateUserForm";
import { UnauthorizedError, requestJson, updateAdminStatus } from "@/lib/api";
import { useRequireAuth } from "@/hooks/use-auth";

// Define the user type based on the backend schema
type AdminUser = {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
  is_confirmed: boolean;
};

// Define the paginated response type
type PaginatedUsersResponse = {
  users: AdminUser[];
  total_count: number;
  skip: number;
  limit: number;
};

export default function AdminUsersContent() {
  const auth = useRequireAuth();
  const router = useRouter();
  
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState("created_at");
  const [sortDirection, setSortDirection] = useState("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const itemsPerPage = 10; // Show 10 users per page

  // Function to load users from the backend
  const loadUsers = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    
    setLoading(true);
    try {
      // Calculate skip based on current page
      const skip = (currentPage - 1) * itemsPerPage;
      
      // Build query parameters
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: itemsPerPage.toString(),
        search: search || "",
        sort_field: sortField,
        sort_direction: sortDirection,
      });
      
      const data = await requestJson<PaginatedUsersResponse>(
        `/admin/users?${params.toString()}`,
        { method: "GET" },
        auth.token,
      );
      
      setUsers(data.users);
      setTotalUsers(data.total_count);
      setTotalPages(Math.ceil(data.total_count / itemsPerPage));
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
  }, [auth, currentPage, search, sortField, sortDirection]);

  // Load users when dependencies change
  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  // Handle search submission
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1); // Reset to first page when searching
  };

  // Handle pagination
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  // Handle sorting
  const handleSort = (field: string) => {
    if (sortField === field) {
      // Toggle sort direction if clicking the same field
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Sort by new field in descending order
      setSortField(field);
      setSortDirection("desc");
    }
    setCurrentPage(1); // Reset to first page when sorting
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

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
          <p className="font-semibold">Error loading users</p>
          <p>{error}</p>
          <Button onClick={() => void loadUsers()} className="mt-4">
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <CreateUserForm onUserCreated={loadUsers} />
      <Card>
        <CardContent className="p-0 mt-4">
          <div className="flex gap-2 mb-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                placeholder="Search by email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
              <Button type="submit">Search</Button>
            </form>
          </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort("id")}
                >
                  <div className="flex items-center">
                    <span>ID</span>
                    {sortField === "id" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort("email")}
                >
                  <div className="flex items-center">
                    <span>Email</span>
                    {sortField === "email" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort("created_at")}
                >
                  <div className="flex items-center">
                    <span>Registration Date</span>
                    {sortField === "created_at" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort("is_confirmed")}
                >
                  <div className="flex items-center">
                    <span>Account Status</span>
                    {sortField === "is_confirmed" && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Admin Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr 
                    key={user.id} 
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => router.push(`/admin/users/${user.id}`)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                      {user.id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <Badge variant={user.is_confirmed ? "default" : "destructive"}>
                        {user.is_confirmed ? "Confirmed" : "Unconfirmed"}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center" onClick={(e) => e.stopPropagation()}>
                        <Badge variant={user.is_admin ? "default" : "outline"}>
                          {user.is_admin ? "Admin" : "User"}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="ml-2 h-7"
                          onClick={async () => {
                            if (!auth.token) {
                              toast.error("Authentication token is missing");
                              return;
                            }
                            try {
                              const response = await updateAdminStatus(
                                auth.token,
                                user.id,
                                !user.is_admin
                              );
                              toast.success(`User status updated to ${response.is_admin ? "admin" : "user"}`);
                              // Refresh the user list
                              void loadUsers();
                            } catch (error) {
                              const message = error instanceof Error ? error.message : "Failed to update user admin status";
                              toast.error(message);
                            }
                          }}
                        >
                          {user.is_admin ? "Demote" : "Promote"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="border-t px-6 py-4 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span> to 
            <span className="font-medium"> {Math.min(currentPage * itemsPerPage, totalUsers)}</span> of 
            <span className="font-medium"> {totalUsers}</span> results
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            
            {/* Page numbers */}
            {totalPages <= 7 ? (
              // If total pages is 7 or less, show all pages
              Array.from({ length: totalPages }, (_, i) => (
                <Button
                  key={i + 1}
                  variant={currentPage === i + 1 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePageChange(i + 1)}
                >
                  {i + 1}
                </Button>
              ))
            ) : (
              // If total pages is more than 7, show first, current (with neighbors), and last
              <>
                <Button
                  variant={currentPage === 1 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePageChange(1)}
                >
                  1
                </Button>
                
                {currentPage > 3 && (
                  <span className="px-2 flex items-center">...</span>
                )}
                
                {currentPage > 2 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                  >
                    {currentPage - 1}
                  </Button>
                )}
                
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handlePageChange(currentPage)}
                >
                  {currentPage}
                </Button>
                
                {currentPage < totalPages - 1 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                  >
                    {currentPage + 1}
                  </Button>
                )}
                
                {currentPage < totalPages - 2 && (
                  <span className="px-2 flex items-center">...</span>
                )}
                
                <Button
                  variant={currentPage === totalPages ? "default" : "outline"}
                  size="sm"
                  onClick={() => handlePageChange(totalPages)}
                >
                  {totalPages}
                </Button>
              </>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
    </div>
  );
}