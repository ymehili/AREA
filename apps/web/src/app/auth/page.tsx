"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Zap, Shield, Clock } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, PasswordInput } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OAuthButton } from "@/components/ui/oauth-button";
import { useAuth } from "@/hooks/use-auth";
import { cn, headingClasses } from "@/lib/utils";

function AuthPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const auth = useAuth();
  
  // Check if user came from "Sign In" button (default to register for "Get Started")
  const initialMode = searchParams.get("mode") === "login" ? "login" : "register";
  const [mode, setMode] = useState<"login" | "register">(initialMode);
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
    <div className="min-h-screen bg-background relative flex flex-col">
      {/* Back to Home Button */}
      <div className="absolute top-6 left-6 z-10">
        <Button
          variant="outline"
          size="default"
          onClick={() => router.push("/")}
          className="group border-2 hover:border-primary hover:bg-primary/5 transition-all duration-200 shadow-sm hover:shadow-md"
        >
          <ArrowLeft className="mr-2 h-4 w-4 group-hover:-translate-x-1 transition-transform duration-200" />
          <span className="font-medium">Back to Home</span>
        </Button>
      </div>

      {/* Centered Auth Form with Benefits Below */}
      <div className="container mx-auto px-4 flex-1 flex flex-col justify-center py-12">
        <div className="max-w-md mx-auto w-full">
          <Card className="p-8 shadow-xl border-2 border-primary/10 bg-card/50 backdrop-blur-sm">
            <CardHeader className="p-0 mb-8">
              <CardTitle className={cn(headingClasses(1), "text-foreground text-center text-3xl")}>
                ACTION-REACTION
              </CardTitle>
              <p className="text-center text-muted-foreground mt-3 text-base">
                {mode === "login" ? "Welcome back! Sign in to continue." : "Create your account to get started."}
              </p>
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
            <TabsList className="grid grid-cols-2 mb-8 p-1 bg-muted/50">
              <TabsTrigger value="login" className="data-[state=active]:bg-background data-[state=active]:shadow-sm">Log in</TabsTrigger>
              <TabsTrigger value="register" className="data-[state=active]:bg-background data-[state=active]:shadow-sm">Register</TabsTrigger>
            </TabsList>
            <TabsContent value="login">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="text-foreground font-medium">Email</Label>
                    <Input
                      id="login-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="bg-background border-input h-11 focus-visible:ring-2 focus-visible:ring-primary"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="text-foreground font-medium">Password</Label>
                    <PasswordInput
                      id="login-password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="bg-background border-input h-11 focus-visible:ring-2 focus-visible:ring-primary"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full h-11 text-base font-medium shadow-md hover:shadow-lg transition-shadow" disabled={isBusy}>
                  {isBusy ? "Signing in…" : "Continue"}
                </Button>
                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-3 bg-card text-muted-foreground font-medium">Or continue with</span>
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
                <div className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="register-email" className="text-foreground font-medium">Email</Label>
                    <Input
                      id="register-email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="bg-background border-input h-11 focus-visible:ring-2 focus-visible:ring-primary"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password" className="text-foreground font-medium">Password</Label>
                    <PasswordInput
                      id="register-password"
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                      className="bg-background border-input h-11 focus-visible:ring-2 focus-visible:ring-primary"
                      placeholder="Minimum 8 characters"
                    />
                  </div>
                </div>
                <Button type="submit" className="w-full h-11 text-base font-medium shadow-md hover:shadow-lg transition-shadow" disabled={isBusy}>
                  {isBusy ? "Creating account…" : "Create account"}
                </Button>
                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-3 bg-card text-muted-foreground font-medium">Or continue with</span>
                  </div>
                </div>
                <div className="space-y-3">
                  <OAuthButton
                    provider="google"
                    action="signup"
                    onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_BASE_URL}/oauth/google`}
                  />
                  <OAuthButton
                    provider="github"
                    action="signup"
                    onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_BASE_URL}/service-connections/connect/github`}
                  />
                  <OAuthButton
                    provider="microsoft"
                    action="signup"
                    onClick={() => toast.info("Microsoft OAuth coming soon!")}
                  />
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
        </div>

      {/* Benefits Section Below Form */}
      <div className="mt-8 mb-12 max-w-4xl mx-auto w-full">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="flex flex-col items-center text-center p-8 rounded-xl bg-card border-2 border-primary/10 shadow-md hover:shadow-lg hover:border-primary/30 transition-all duration-300">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center mb-4 shadow-sm">
              <Zap className="h-7 w-7 text-primary" />
            </div>
            <h3 className="font-bold text-foreground mb-2 text-lg">Quick Setup</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Create your first automation in under 5 minutes. No coding required.
            </p>
          </div>
          
          <div className="flex flex-col items-center text-center p-8 rounded-xl bg-card border-2 border-primary/10 shadow-md hover:shadow-lg hover:border-primary/30 transition-all duration-300">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center mb-4 shadow-sm">
              <Shield className="h-7 w-7 text-primary" />
            </div>
            <h3 className="font-bold text-foreground mb-2 text-lg">Secure & Private</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Enterprise-grade security with OAuth2 and encrypted connections.
            </p>
          </div>
          
          <div className="flex flex-col items-center text-center p-8 rounded-xl bg-card border-2 border-primary/10 shadow-md hover:shadow-lg hover:border-primary/30 transition-all duration-300">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center mb-4 shadow-sm">
              <Clock className="h-7 w-7 text-primary" />
            </div>
            <h3 className="font-bold text-foreground mb-2 text-lg">Save Time Daily</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Automate repetitive tasks and focus on what matters most.
            </p>
          </div>
        </div>

        {/* Social Proof */}
        <div className="mt-10 text-center">
          <p className="text-sm text-muted-foreground mb-4 font-medium">Trusted by professionals at</p>
          <div className="flex items-center justify-center space-x-6 text-foreground/70 font-semibold text-sm">
            <span className="hover:text-primary transition-colors cursor-default">Google</span>
            <span className="text-muted-foreground">•</span>
            <span className="hover:text-primary transition-colors cursor-default">Microsoft</span>
            <span className="text-muted-foreground">•</span>
            <span className="hover:text-primary transition-colors cursor-default">GitHub</span>
            <span className="text-muted-foreground">•</span>
            <span className="hover:text-primary transition-colors cursor-default">Discord</span>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" role="status">
            <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">Loading...</span>
          </div>
        </div>
      </div>
    }>
      <AuthPageContent />
    </Suspense>
  );
}
