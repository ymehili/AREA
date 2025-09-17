import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ConfirmationSuccessPage() {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle>Email confirmed</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-muted-foreground">
            Your Action-Reaction account is now active. You can sign in with your email and password to
            start building automations.
          </p>
          <Button asChild size="lg" className="w-full">
            <Link href="/">Go to login</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
