"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OAuthButton } from "@/components/ui/oauth-button";
import { useAuth } from "@/hooks/use-auth";
import { cn, headingClasses } from "@/lib/utils";

export default function AuthPage() {
  const router = useRouter();
  const auth = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!auth.initializing && auth.token) {
      router.replace("/dashboard");
    }
  }, [auth.initializing, auth.token, router]);

  const isBusy = submitting || auth.loading;

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      if (mode === "login") {
        await auth.login(email, password);
        toast.success("Logged in successfully");
        router.replace("/dashboard");
      } else {
        await auth.register(email, password);
        toast.success("Registration received. Check your email to confirm your account.");
        setMode("login");
        setPassword("");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-background">
      <Card className="w-full max-w-md p-6">
        <CardHeader className="p-0 mb-6">
          <CardTitle className={cn(headingClasses(1), "text-foreground text-center")}>
            Action-Reaction
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {auth.pendingConfirmationEmail ? (
            <Alert className="mb-4">
              <AlertTitle>Confirm your email</AlertTitle>
              <AlertDescription>
                We sent a confirmation link to{" "}
                <span className="font-medium text-foreground">{auth.pendingConfirmationEmail}</span>. Once
                confirmed, you can log in with your credentials.
              </AlertDescription>
            </Alert>
          ) : null}
          <Tabs value={mode} onValueChange={(value) => setMode(value as typeof mode)}>
            <TabsList className="grid grid-cols-2 mb-6">
              <TabsTrigger value="login">Log in</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>
            <TabsContent value="login">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="text-foreground">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="bg-background border-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="text-foreground">Password</Label>
                    <PasswordInput
                      id="login-password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="bg-background border-input"
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full" disabled={isBusy}>
                  {isBusy ? "Signing in…" : "Continue"}
                </Button>
                <div className="relative my-4">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-input" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-background text-foreground">Or continue with</span>
                  </div>
                </div>
                <div className="space-y-3">
                  <OAuthButton
                    provider="google"
                    onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_BASE_URL}/oauth/google`}
                  />
                  <OAuthButton
                    provider="github"
                    onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_BASE_URL}/service-connections/connect/github`}
                  />
                  <OAuthButton
                    provider="microsoft"
                    onClick={() => toast.info("Microsoft OAuth coming soon!")}
                  />
                </div>
              </form>
            </TabsContent>
            <TabsContent value="register">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-email" className="text-foreground">Email</Label>
                    <Input
                      id="register-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="bg-background border-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password" className="text-foreground">Password</Label>
                    <PasswordInput
                      id="register-password"
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      className="bg-background border-input"
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full" disabled={isBusy}>
                  {isBusy ? "Creating account…" : "Create account"}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
