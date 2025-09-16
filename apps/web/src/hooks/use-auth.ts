"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuthContext } from "@/components/auth-provider";

export function useAuth() {
  return useAuthContext();
}

export function useRequireAuth() {
  const router = useRouter();
  const auth = useAuthContext();

  useEffect(() => {
    if (!auth.initializing && !auth.token) {
      router.replace("/");
    }
  }, [auth.initializing, auth.token, router]);

  return auth;
}
