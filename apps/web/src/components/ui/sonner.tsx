"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      position="bottom-right"
      style={
        {
          "--toast-bg": "hsl(var(--background))",
          "--toast-border": "hsl(var(--border))",
          "--toast-color": "hsl(var(--foreground))",
          "--toast-description-color": "hsl(var(--muted-foreground))",
        } as React.CSSProperties
      }
      toastOptions={{
        style: {
          background: "white",
          color: "hsl(var(--foreground))",
          borderRadius: "calc(var(--radius) - 2px)",
          border: "1px solid hsl(var(--border))",
          backdropFilter: "none",
        },
        duration: 5000,
      }}
      {...props}
    />
  )
}

export { Toaster }
