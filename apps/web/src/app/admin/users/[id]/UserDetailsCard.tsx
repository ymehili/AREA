import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type UserDetail = {
  id: string;
  email: string;
  full_name: string | null;
  is_confirmed: boolean;
  is_admin: boolean;
  is_suspended: boolean;
  created_at: string;
  confirmed_at: string | null;
};

export default function UserDetailsCard({ user }: { user: UserDetail }) {
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

  return (
    <Card>
      <CardHeader>
        <CardTitle>User Information</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-medium text-gray-500">User ID</h3>
            <p className="text-sm font-mono">{user.id}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Email</h3>
            <p className="text-sm">{user.email}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Full Name</h3>
            <p className="text-sm">{user.full_name || '-'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Registration Date</h3>
            <p className="text-sm">{formatDate(user.created_at)}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Account Status</h3>
            <div className="flex space-x-2 mt-1">
              <Badge variant={user.is_confirmed ? "default" : "destructive"}>
                {user.is_confirmed ? "Confirmed" : "Unconfirmed"}
              </Badge>
              <Badge variant={user.is_suspended ? "destructive" : "secondary"}>
                {user.is_suspended ? "Suspended" : "Active"}
              </Badge>
              <Badge variant={user.is_admin ? "secondary" : "outline"}>
                {user.is_admin ? "Admin" : "User"}
              </Badge>
            </div>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Confirmation Date</h3>
            <p className="text-sm">{user.confirmed_at ? formatDate(user.confirmed_at) : '-'}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}