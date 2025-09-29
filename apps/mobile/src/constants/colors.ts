// Color Palette from UI/UX Specs
export const Colors = {
  // Primary
  primary: '#0052FF',           // The main brand color, used for primary buttons, links, and key UI elements
  primaryForeground: '#FFFFFF', // White text on primary
  
  // Accent
  accent: '#FF4700',            // A high-visibility accent, used for highlights, notifications, and specific CTAs
  accentForeground: '#FFFFFF',  // White text on accent
  
  // Secondary Accent
  secondaryAccent: '#00E0FF',   // A secondary accent for code-related elements, tags, or subtle highlights
  
  // Highlight
  highlight: '#A8BFFF',         // A lighter blue for backgrounds, hover states, or subtle geometric patterns
  
  // Success
  success: '#00C853',           // For success messages, confirmations, and positive feedback
  successForeground: '#FFFFFF', // White text on success
  
  // Warning
  warning: '#FFAB00',           // For warnings, important notices, and non-critical alerts
  warningForeground: '#000000', // Black text on warning
  
  // Error
  error: '#D50000',             // For error messages, validation failures, and destructive action confirmations
  errorForeground: '#FFFFFF',   // White text on error
  
  // Neutral
  text: '#FFFFFF',              // Primary text color for high contrast against the blue background (in dark mode)
  textDark: '#0042CC',          // Primary text color for light mode
  border: '#3375FF',            // For subtle borders and dividers that complement the primary blue
  background: '#0042CC',        // A slightly darker blue for card backgrounds or secondary panels (dark mode)
  backgroundLight: '#FFFFFF',   // Light mode background
  card: '#0042CC',              // Card background (dark mode)
  cardLight: '#FFFFFF',         // Card background (light mode)
  muted: '#A8BFFF',             // Muted backgrounds
  mutedForeground: '#3375FF',   // Muted text
  input: '#3375FF',             // Input border
  popover: '#0042CC',           // Popover background (dark mode)
  popoverLight: '#FFFFFF',      // Popover background (light mode)
  popoverForeground: '#FFFFFF', // Popover text (dark mode)
  popoverForegroundDark: '#0042CC', // Popover text (light mode)
  
  // Secondary
  secondary: '#3375FF',         // Secondary blue
  secondaryForeground: '#0042CC', // Secondary blue text in dark mode
  secondaryForegroundLight: '#FFFFFF', // Secondary blue text in light mode
};

// Theme object to support both light and dark modes
export const Theme = {
  light: {
    background: Colors.backgroundLight,
    text: Colors.textDark,
    card: Colors.cardLight,
    border: Colors.border,
    primary: Colors.primary,
    accent: Colors.accent,
    error: Colors.error,
    muted: Colors.muted,
    mutedForeground: Colors.mutedForeground,
    input: Colors.input,
    success: Colors.success,
    warning: Colors.warning,
  },
  dark: {
    background: Colors.background,
    text: Colors.text,
    card: Colors.card,
    border: Colors.border,
    primary: Colors.primary,
    accent: Colors.accent,
    error: Colors.error,
    muted: Colors.muted,
    mutedForeground: Colors.mutedForeground,
    input: Colors.input,
    success: Colors.success,
    warning: Colors.warning,
  }
};