"use client";

import Link from "next/link";
import { Star, Users, Copy } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Template } from "@/lib/types/marketplace";

interface TemplateCardProps {
  template: Template;
}

export function TemplateCard({ template }: TemplateCardProps) {
  return (
    <Link href={`/marketplace/${template.id}`} className="block">
      <Card className="h-full transition-all hover:shadow-md hover:border-primary/50 cursor-pointer">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="line-clamp-2 text-lg">{template.title}</CardTitle>
            <Badge variant="secondary" className="shrink-0">
              {template.category}
            </Badge>
          </div>
          <CardDescription className="line-clamp-3">{template.description}</CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Tags */}
          {template.tags && template.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {template.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {template.tags.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{template.tags.length - 3}
                </Badge>
              )}
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Users className="h-4 w-4" />
              <span>{template.usage_count.toLocaleString()}</span>
            </div>
            
            <div className="flex items-center gap-1">
              <Copy className="h-4 w-4" />
              <span>{template.clone_count.toLocaleString()}</span>
            </div>
            
            {template.rating_average !== null && (
              <div className="flex items-center gap-1">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                <span>{template.rating_average.toFixed(1)}</span>
                <span className="text-xs">({template.rating_count})</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
