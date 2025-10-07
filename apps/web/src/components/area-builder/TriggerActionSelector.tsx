import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { getServiceCatalog, ServiceCatalogResponse, ServiceCatalogItem, ServiceOption } from '@/lib/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface TriggerActionSelectorProps {
  nodeType: 'trigger' | 'action';
  onServiceSelect: (serviceId: string) => void;
  onActionSelect: (actionId: string) => void;
  selectedServiceId?: string;
  selectedActionId?: string;
  label: string;
  description: string;
}

const TriggerActionSelector: React.FC<TriggerActionSelectorProps> = ({
  nodeType,
  onServiceSelect,
  onActionSelect,
  selectedServiceId,
  selectedActionId,
  label,
  description,
}) => {
  const { token } = useAuth();
  const [catalog, setCatalog] = useState<ServiceCatalogItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Get the action/reaction list based on node type and selected service
  const selectedService = catalog?.find(service => service.slug === selectedServiceId);
  const availableActions = nodeType === 'trigger' 
    ? selectedService?.actions || [] 
    : selectedService?.reactions || [];

  useEffect(() => {
    if (!token) return;

    const fetchCatalog = async () => {
      try {
        setLoading(true);
        const data = await getServiceCatalog(token);
        setCatalog(data.services);
        setError(null);
      } catch (err) {
        console.error('Error fetching service catalog:', err);
        setError('Failed to load services. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchCatalog();
  }, [token]);

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>{label}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">Loading services...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>{label}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-500">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{label}</CardTitle>
          <Badge variant={nodeType === 'trigger' ? 'secondary' : 'secondary'} 
                 className={nodeType === 'trigger' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'}>
            {nodeType === 'trigger' ? 'TRIGGER' : 'ACTION'}
          </Badge>
        </div>
        <p className="text-sm text-gray-500">{description}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Select Service</label>
          <Select value={selectedServiceId} onValueChange={onServiceSelect}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Choose a service..." />
            </SelectTrigger>
            <SelectContent>
              {catalog?.map(service => (
                <SelectItem key={service.slug} value={service.slug}>
                  {service.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {selectedServiceId && (
          <div>
            <label className="block text-sm font-medium mb-2">
              {nodeType === 'trigger' ? 'Select Trigger' : 'Select Action'}
            </label>
            <Select value={selectedActionId} onValueChange={onActionSelect}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={`Choose a ${nodeType}...`} />
              </SelectTrigger>
              <SelectContent>
                {availableActions.map(action => (
                  <SelectItem key={action.key} value={action.key}>
                    <div>
                      <span className="font-medium">{action.name}</span>
                      <p className="text-xs text-gray-500 mt-1">{action.description}</p>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {selectedServiceId && selectedActionId && (
          <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
            <p className="text-sm">
              <span className="font-medium">Selected:</span> {selectedServiceId} - {selectedActionId}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TriggerActionSelector;