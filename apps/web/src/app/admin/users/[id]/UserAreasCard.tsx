import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Area = {
  id: string;
  name: string;
  trigger_service: string;
  reaction_service: string;
  enabled: boolean;
  created_at: string;
};

export default function UserAreasCard({ 
  areas 
}: { 
  areas: Area[] 
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
        <CardTitle>User&apos;s AREAs</CardTitle>
      </CardHeader>
      <CardContent>
        {areas.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No AREAs created</p>
        ) : (
          <div className="space-y-3">
            {areas.map((area) => (
              <div key={area.id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium truncate">{area.name}</h4>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs px-2 py-1 bg-gray-200 rounded capitalize">{area.trigger_service}</span>
                      <span className="text-xs text-gray-500">→</span>
                      <span className="text-xs px-2 py-1 bg-gray-200 rounded capitalize">{area.reaction_service}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end ml-2">
                    <Badge variant={area.enabled ? "default" : "destructive"}>
                      {area.enabled ? "Active" : "Inactive"}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1">{formatDate(area.created_at)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}