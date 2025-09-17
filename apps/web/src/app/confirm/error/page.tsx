import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ConfirmationErrorPage() {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle>Link could not be verified</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-muted-foreground">
            The confirmation link is no longer valid. Try logging in to request a new confirmation email, or
            contact support if the issue persists.
          </p>
          <Button asChild size="lg" className="w-full" variant="secondary">
            <Link href="/">Back to login</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
