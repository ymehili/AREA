"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, headingClasses } from "@/lib/utils";
import { 
  Zap, 
  Link2, 
  Sparkles, 
  ArrowRight, 
  Mail, 
  Cloud,
  Github,
  MessageSquare,
  Calendar,
  Brain,
  CloudRain,
  Languages
} from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const auth = useAuth();

  useEffect(() => {
    if (!auth.initializing && auth.token) {
      router.replace("/dashboard");
    }
  }, [auth.initializing, auth.token, router]);

  // Show nothing while checking auth to prevent flash
  if (auth.initializing || auth.token) {
    return null;
  }

  const features = [
    {
      icon: Zap,
      title: "Instant Automation",
      description: "Connect your favorite apps and automate workflows in minutes, no coding required."
    },
    {
      icon: Link2,
      title: "Seamless Integration",
      description: "Link multiple services together with our powerful OAuth2 authentication system."
    },
    {
      icon: Sparkles,
      title: "Smart Triggers",
      description: "Set up intelligent triggers that respond to events across all your connected services."
    }
  ];

  const services = [
    { name: "Time", icon: Zap, color: "text-primary" },
    { name: "Debug", icon: Sparkles, color: "text-foreground" },
    { name: "Delay", icon: Link2, color: "text-muted-foreground" },
    { name: "Gmail", icon: Mail, color: "text-destructive" },
    { name: "Outlook", icon: Mail, color: "text-primary" },
    { name: "Google Drive", icon: Cloud, color: "text-primary" },
    { name: "GitHub", icon: Github, color: "text-foreground" },
    { name: "Weather", icon: CloudRain, color: "text-accent-foreground" },
    { name: "OpenAI", icon: Brain, color: "text-success" },
    { name: "Discord", icon: MessageSquare, color: "text-accent-foreground" },
    { name: "Google Calendar", icon: Calendar, color: "text-primary" },
    { name: "DeepL Translate", icon: Languages, color: "text-primary" }
  ];

  const useCases = [
    {
      trigger: "New GitHub Issue",
      action: "Send Email",
      description: "Get notified via email when a new issue is created in your repository"
    },
    {
      trigger: "New Email Received",
      action: "Save to Google Drive",
      description: "Automatically backup email attachments to Google Drive"
    },
    {
      trigger: "Temperature Threshold",
      action: "Get Current Weather",
      description: "Get current weather data when temperature reaches a specified threshold"
    },
    {
      trigger: "Event Created",
      action: "Create Event",
      description: "Automatically create a new event in Google Calendar when an event is detected"
    },
    {
      trigger: "New Message in Channel",
      action: "Send Message to Channel",
      description: "Reply to a message in a Discord channel when a new message arrives"
    },
    {
      trigger: "Push to Repository",
      action: "Create Issue",
      description: "Create a new issue in a repository when code is pushed"
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky Navigation Header */}
      <nav className="sticky top-0 z-50 bg-background/95 backdrop-blur-sm border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className={cn(headingClasses(1), "text-xl md:text-2xl text-primary")}>
              ACTION-REACTION
            </div>
            <div className="flex items-center gap-4">
              <Button 
                variant="ghost" 
                onClick={() => router.push("/auth?mode=login")}
                className="hidden sm:inline-flex"
              >
                Sign In
              </Button>
              <Button 
                onClick={() => router.push("/auth")}
                className="group"
              >
                Get Started
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Decorative geometric shapes */}
        <div className="absolute inset-0 overflow-hidden opacity-10">
          <div className="absolute top-20 left-10 w-64 h-64 bg-primary rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent-foreground rounded-full blur-3xl" />
        </div>

        <div className="relative container mx-auto px-4 pt-20 pb-32">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            {/* Logo/Brand */}
            <div className="inline-block">
              <h1 className={cn(
                headingClasses(1),
                "text-5xl md:text-7xl tracking-wider text-primary mb-4"
              )}>
                ACTION-REACTION
              </h1>
              <div className="h-1 w-full bg-gradient-to-r from-primary via-accent-foreground to-primary rounded-full" />
            </div>

            {/* Tagline */}
            <p className="text-xl md:text-2xl text-foreground/80 font-medium max-w-2xl mx-auto">
              Automate your workflow by connecting your favorite apps. 
              Create powerful automations in minutes, not hours.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
              <Button 
                size="lg" 
                className="text-lg px-8 py-6 group"
                onClick={() => router.push("/auth")}
              >
                Get Started Free
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button 
                variant="outline" 
                size="lg" 
                className="text-lg px-8 py-6"
                onClick={() => router.push("/auth?mode=login")}
              >
                Sign In
              </Button>
            </div>

            {/* Stats/Social Proof */}
            <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto pt-12 border-t border-border">
              <div>
                <div className={cn(headingClasses(2), "text-3xl text-primary")}>15+</div>
                <p className="text-sm text-muted-foreground mt-1">Integrations</p>
              </div>
              <div>
                <div className={cn(headingClasses(2), "text-3xl text-primary")}>10K+</div>
                <p className="text-sm text-muted-foreground mt-1">Automations</p>
              </div>
              <div>
                <div className={cn(headingClasses(2), "text-3xl text-primary")}>5K+</div>
                <p className="text-sm text-muted-foreground mt-1">Active Users</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-muted/20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className={cn(headingClasses(2), "text-4xl text-foreground mb-4")}>
              POWERFUL FEATURES
            </h2>
            <p className="text-lg text-foreground/70 max-w-2xl mx-auto">
              Everything you need to automate your workflow and boost productivity
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {features.map((feature, index) => (
              <Card key={index} className="border-2 hover:border-primary transition-colors duration-300">
                <CardHeader>
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                    <feature.icon className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle className="text-xl">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Services Integration Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className={cn(headingClasses(2), "text-4xl text-foreground mb-4")}>
              CONNECT YOUR APPS
            </h2>
            <p className="text-lg text-foreground/70 max-w-2xl mx-auto">
              Integrate with all your favorite services and create powerful workflows
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-6 max-w-4xl mx-auto mb-12">
            {services.map((service, index) => (
              <div 
                key={index}
                className="flex flex-col items-center space-y-3 p-6 rounded-xl border-2 border-border hover:border-primary transition-all duration-300 hover:scale-105 min-w-[140px]"
              >
                <service.icon className={cn("h-12 w-12", service.color)} />
                <span className="font-medium text-sm">{service.name}</span>
              </div>
            ))}
          </div>

          <div className="text-center">
            <p className="text-muted-foreground">
              Connect your favorite services and create powerful automations
            </p>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 bg-muted/20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className={cn(headingClasses(2), "text-4xl text-foreground mb-4")}>
              HOW IT WORKS
            </h2>
            <p className="text-lg text-foreground/70 max-w-2xl mx-auto">
              Create automations that trigger actions across your connected services
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {useCases.map((useCase, index) => (
              <Card key={index} className="border-2 hover:shadow-lg transition-all duration-300">
                <CardHeader>
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-primary">WHEN</div>
                      <div className="text-base font-semibold">{useCase.trigger}</div>
                    </div>
                  </div>
                  <div className="flex items-center ml-11">
                    <ArrowRight className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex items-center space-x-3 mt-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-foreground text-primary-foreground flex items-center justify-center">
                      <Zap className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-accent-foreground">THEN</div>
                      <div className="text-base font-semibold">{useCase.action}</div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{useCase.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent-foreground/10" />
        
        <div className="relative container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            <h2 className={cn(headingClasses(2), "text-4xl md:text-5xl text-foreground")}>
              READY TO AUTOMATE?
            </h2>
            <p className="text-xl text-foreground/80">
              Join thousands of users who are saving time and boosting productivity with Action-Reaction
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button 
                size="lg" 
                className="text-lg px-8 py-6 group"
                onClick={() => router.push("/auth")}
              >
                Start Free Today
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              No credit card required • Free forever plan available
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12">
        <div className="container mx-auto px-4">
          <div className="text-center text-sm text-muted-foreground">
            <p>© 2025 Action-Reaction. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
