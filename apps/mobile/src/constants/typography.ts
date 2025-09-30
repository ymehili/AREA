// Typography from UI/UX Specs
import { TextStyle } from 'react-native';

// Define font families
export const FontFamilies = {
  heading: 'DelaGothicOne_400Regular', // Dela Gothic One for headings
  body: 'Inter_400Regular',           // Inter for body text
  bodyMedium: 'Inter_500Medium',      // Inter medium for emphasis
  bodyBold: 'Inter_700Bold',          // Inter bold as needed
  mono: 'RobotoMono_400Regular',      // Roboto Mono for code snippets
};

// Define font sizes based on the spec
export const FontSizes = {
  h1: 36,    // H1: 36px - ALL CAPS with letter-spacing: 1.5px
  h2: 28,    // H2: 28px - ALL CAPS with letter-spacing: 1px
  h3: 20,    // H3: 20px - Bold
  body: 16,  // Body: 16px - Regular
  small: 14, // Small: 14px - For helper text
};

// Define font weights
export const FontWeights = {
  regular: '400',
  medium: '500',
  bold: '700',
};

// Predefined text styles following the spec
export const TextStyles: Record<string, TextStyle> = {
  h1: {
    fontFamily: FontFamilies.heading,
    fontSize: FontSizes.h1,
    fontWeight: '400' as const,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
  },
  h2: {
    fontFamily: FontFamilies.heading,
    fontSize: FontSizes.h2,
    fontWeight: '400' as const,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  h3: {
    fontFamily: FontFamilies.body,
    fontSize: FontSizes.h3,
    fontWeight: '700' as const,
  },
  body: {
    fontFamily: FontFamilies.body,
    fontSize: FontSizes.body,
    fontWeight: '400' as const,
  },
  small: {
    fontFamily: FontFamilies.body,
    fontSize: FontSizes.small,
    fontWeight: '400' as const,
  },
  'body-bold': {
    fontFamily: FontFamilies.body,
    fontSize: FontSizes.body,
    fontWeight: '700' as const,
  },
  'small-bold': {
    fontFamily: FontFamilies.body,
    fontSize: FontSizes.small,
    fontWeight: '700' as const,
  },
  mono: {
    fontFamily: FontFamilies.mono,
    fontSize: FontSizes.body,
    fontWeight: '400' as const,
  },
};