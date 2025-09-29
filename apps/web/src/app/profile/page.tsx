"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { cn, headingClasses } from "@/lib/utils";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useRequireAuth } from "@/hooks/use-auth";
import {
  ApiError,
  LoginMethodStatus,
  UnauthorizedError,
  UserProfile,
  changePassword,
  fetchProfile,
  linkLoginMethod,
  unlinkLoginMethod,
  updateProfile,
} from "@/lib/api";
import { toast } from "sonner";

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google",
  github: "GitHub",
  microsoft: "Microsoft",
};

type ProfileFormState = {
  fullName: string;
  email: string;
};

type PasswordFormState = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

export default function ProfilePage() {
  const auth = useRequireAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileFormState>({ fullName: "", email: "" });
  const [passwordForm, setPasswordForm] = useState<PasswordFormState>({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [profileSaving, setProfileSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [providerPending, setProviderPending] = useState<Record<string, boolean>>({});

  const handleApiError = useCallback(
    (error: unknown, fallback: string): string | null => {
      if (error instanceof UnauthorizedError) {
        toast.error("Session expired. Please sign in again.");
        auth.logout();
        return null;
      }
      if (error instanceof ApiError) {
        toast.error(error.message);
        return error.message;
      }
      toast.error(fallback);
      return fallback;
    },
    [auth],
  );

  const loadProfile = useCallback(async () => {
    if (!auth.token) {
      return;
    }
    setLoading(true);
    try {
      const data = await fetchProfile(auth.token);
      setProfile(data);
      setProfileForm({
        fullName: data.full_name ?? "",
        email: data.email,
      });
      setLoadError(null);
    } catch (error) {
      const message = handleApiError(error, "Unable to load profile.");
      if (message) {
        setLoadError(message);
      }
    } finally {
      setLoading(false);
    }
  }, [auth.token, handleApiError]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const isProviderPending = useCallback(
    (provider: string) => providerPending[provider] ?? false,
    [providerPending],
  );

  const updateLoginMethodStatus = useCallback((nextStatus: LoginMethodStatus) => {
    setProfile((prev) => {
      if (!prev) {
        return prev;
      }
      return {
        ...prev,
        login_methods: prev.login_methods.map((method) =>
          method.provider === nextStatus.provider ? nextStatus : method,
        ),
      };
    });
  }, []);

  const profileAlert = useMemo(() => {
    if (!profile || profile.is_confirmed) {
      return null;
    }
    return (
      <Alert className="mb-4" variant="destructive">
        <AlertTitle>Email confirmation required</AlertTitle>
        <AlertDescription>
          We sent a confirmation link to <span className="font-medium">{profile.email}</span>. You
          need to confirm the new address before logging in again.
        </AlertDescription>
      </Alert>
    );
  }, [profile]);

  const submitProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!auth.token || !profile) {
      return;
    }

    setProfileSaving(true);
    try {
      const payload = {
        full_name: profileForm.fullName.trim() === "" ? null : profileForm.fullName,
        email: profileForm.email.trim(),
      };
      const updated = await updateProfile(auth.token, payload);
      setProfile(updated);
      setProfileForm({
        fullName: updated.full_name ?? "",
        email: updated.email,
      });
      auth.setEmail(updated.email);

      if (!updated.is_confirmed) {
        toast.success("Email updated. Please confirm the new address sent to your inbox.");
      } else {
        toast.success("Profile updated.");
      }
    } catch (error) {
      handleApiError(error, "Unable to update your profile.");
    } finally {
      setProfileSaving(false);
    }
  };

  const submitPassword = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!auth.token || !profile) {
      return;
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error("New password and confirmation must match.");
      return;
    }

    setPasswordSaving(true);
    try {
      const updated = await changePassword(auth.token, {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      });
      setProfile(updated);
      setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      toast.success("Password updated successfully.");
    } catch (error) {
      handleApiError(error, "Unable to change your password.");
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleLink = async (provider: string) => {
    if (!auth.token) {
      return;
    }
    const label = PROVIDER_LABELS[provider] ?? provider;
    const identifier = window.prompt(`Enter the ${label} account identifier to link.`);
    if (!identifier) {
      return;
    }
    const sanitized = identifier.trim();
    if (!sanitized) {
      toast.error("An identifier is required to link this login method.");
      return;
    }

    setProviderPending((prev) => ({ ...prev, [provider]: true }));
    try {
      const status = await linkLoginMethod(auth.token, provider, sanitized);
      updateLoginMethodStatus(status);
      toast.success(`${label} account linked.`);
    } catch (error) {
      handleApiError(error, `Unable to link ${label}.`);
    } finally {
      setProviderPending((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const handleUnlink = async (provider: string) => {
    if (!auth.token) {
      return;
    }
    const label = PROVIDER_LABELS[provider] ?? provider;
    setProviderPending((prev) => ({ ...prev, [provider]: true }));
    try {
      const status = await unlinkLoginMethod(auth.token, provider);
      updateLoginMethodStatus(status);
      toast.success(`${label} account unlinked.`);
    } catch (error) {
      handleApiError(error, `Unable to unlink ${label}.`);
    } finally {
      setProviderPending((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const content = (() => {
    if (loading) {
      return (
        <div className="flex min-h-[280px] items-center justify-center text-sm text-muted-foreground">
          Loading profile…
        </div>
      );
    }

    if (loadError) {
      return (
        <div className="flex flex-col items-center gap-4 py-12">
          <p className="text-sm text-destructive">{loadError}</p>
          <Button onClick={() => void loadProfile()} variant="outline">
            Retry
          </Button>
        </div>
      );
    }

    if (!profile) {
      return (
        <div className="flex min-h-[280px] items-center justify-center text-sm text-muted-foreground">
          We couldn’t load your profile right now.
        </div>
      );
    }

    return (
      <div className="grid gap-6">
        {profileAlert}

        <Card>
          <form onSubmit={submitProfile} className="grid gap-6">
            <CardHeader>
              <div>
                <CardTitle>Basic information</CardTitle>
                <CardDescription>Update the details shown to other parts of the workspace.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid max-w-md gap-2">
                <Label htmlFor="full-name">Full name</Label>
                <Input
                  id="full-name"
                  value={profileForm.fullName}
                  onChange={(event) => setProfileForm((prev) => ({ ...prev, fullName: event.target.value }))}
                  placeholder="Jane Doe"
                  disabled={profileSaving}
                />
              </div>
              <div className="grid max-w-md gap-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  value={profileForm.email}
                  onChange={(event) => setProfileForm((prev) => ({ ...prev, email: event.target.value }))}
                  disabled={profileSaving}
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button type="submit" disabled={profileSaving}>
                {profileSaving ? "Saving…" : "Save changes"}
              </Button>
            </CardFooter>
          </form>
        </Card>

        {profile.has_password && (
          <Card>
            <form onSubmit={submitPassword} className="grid gap-6">
              <CardHeader>
                <div>
                  <CardTitle>Password</CardTitle>
                  <CardDescription>Change the password used for email sign-in.</CardDescription>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="current-password">Current password</Label>
                  <Input
                    id="current-password"
                    type="password"
                    value={passwordForm.currentPassword}
                    onChange={(event) =>
                      setPasswordForm((prev) => ({ ...prev, currentPassword: event.target.value }))
                    }
                    disabled={passwordSaving}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="new-password">New password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={passwordForm.newPassword}
                    onChange={(event) =>
                      setPasswordForm((prev) => ({ ...prev, newPassword: event.target.value }))
                    }
                    disabled={passwordSaving}
                    required
                    minLength={8}
                  />
                </div>
                <div className="grid gap-2 md:col-span-2">
                  <Label htmlFor="confirm-password">Confirm new password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={passwordForm.confirmPassword}
                    onChange={(event) =>
                      setPasswordForm((prev) => ({ ...prev, confirmPassword: event.target.value }))
                    }
                    disabled={passwordSaving}
                    required
                    minLength={8}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end">
                <Button type="submit" disabled={passwordSaving}>
                  {passwordSaving ? "Updating…" : "Update password"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        )}

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Login methods</CardTitle>
              <CardDescription>Link or unlink third-party accounts to sign into Action-Reaction.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {profile.login_methods.map((method) => {
              const label = PROVIDER_LABELS[method.provider] ?? method.provider;
              const pending = isProviderPending(method.provider);
              return (
                <div
                  key={method.provider}
                  className="flex flex-col gap-2 rounded-lg border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-xs text-muted-foreground">
                      {method.linked
                        ? `Linked as ${method.identifier ?? "hidden identifier"}`
                        : "Not linked"}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {method.linked ? (
                      <Button
                        variant="outline"
                        onClick={() => void handleUnlink(method.provider)}
                        disabled={pending}
                      >
                        {pending ? "Unlinking…" : "Unlink"}
                      </Button>
                    ) : (
                      <Button
                        variant="secondary"
                        onClick={() => void handleLink(method.provider)}
                        disabled={pending}
                        className="text-white"
                      >
                        {pending ? "Linking…" : "Link"}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    );
  })();

  return (
    <div className="space-y-4">
      <h1 className={cn(headingClasses(2), "text-foreground")}>User Profile</h1>
      <Separator />
      {content}
    </div>
  );
}