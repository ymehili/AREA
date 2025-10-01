import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ServiceConnection = {
  id: string;
  service_name: string;
  created_at: string;
};

export default function UserConnectionsCard({ 
  connections 
}: { 
  connections: ServiceConnection[] 
}) {
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
        <CardTitle>Connected Services</CardTitle>
      </CardHeader>
      <CardContent>
        {connections.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No connected services</p>
        ) : (
          <div className="space-y-3">
            {connections.map((connection) => (
              <div key={connection.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <h4 className="font-medium capitalize">{connection.service_name}</h4>
                  <p className="text-xs text-gray-500">Connected: {formatDate(connection.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}