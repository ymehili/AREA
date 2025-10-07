import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface Variable {
  id: string;
  name: string;
  description: string;
  category: string;
  type: 'text' | 'url' | 'number' | 'boolean' | 'object' | 'array';
}

interface VariablePickerProps {
  availableVariables: Variable[];
  onInsertVariable: (variableId: string) => void;
}

const VariablePicker: React.FC<VariablePickerProps> = ({
  availableVariables,
  onInsertVariable,
}) => {
  const [groupedVariables, setGroupedVariables] = useState<Record<string, Variable[]>>({});
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    // Group variables by category
    const grouped: Record<string, Variable[]> = {};
    availableVariables.forEach(variable => {
      if (!grouped[variable.category]) {
        grouped[variable.category] = [];
      }
      grouped[variable.category].push(variable);
    });
    setGroupedVariables(grouped);
  }, [availableVariables]);

  const categories = Object.keys(groupedVariables);

  return (
    <div className="w-full">
      <div className="mb-2">
        <label className="block text-sm font-medium mb-1">Insert Variable</label>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="w-full justify-between">
              {selectedCategory ? selectedCategory : 'Select a service...'} 
              <span className="ml-2 text-xs">▼</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 max-h-60 overflow-y-auto">
            {categories.map(category => (
              <DropdownMenuItem
                key={category}
                onClick={() => setSelectedCategory(category === selectedCategory ? null : category)}
              >
                {category}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {selectedCategory && groupedVariables[selectedCategory] && (
        <div className="mt-3">
          <p className="text-sm font-medium mb-2">Variables from {selectedCategory}:</p>
          <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
            {groupedVariables[selectedCategory].map(variable => (
              <div 
                key={variable.id} 
                className="flex items-center p-2 border rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                onClick={() => onInsertVariable(variable.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{variable.name}</div>
                  <div className="text-xs text-gray-500 truncate">{variable.description}</div>
                </div>
                <div className="ml-2">
                  <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                    variable.type === 'text' ? 'bg-blue-100 text-blue-800' :
                    variable.type === 'url' ? 'bg-green-100 text-green-800' :
                    variable.type === 'number' ? 'bg-yellow-100 text-yellow-800' :
                    variable.type === 'boolean' ? 'bg-purple-100 text-purple-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {variable.type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VariablePicker;