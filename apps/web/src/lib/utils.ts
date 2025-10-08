import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Utility function to apply heading styles according to the specs
export function headingClasses(level: 1 | 2 | 3 = 1): string {
  switch(level) {
    case 1:
      return "font-heading font-normal text-4xl tracking-[0.094rem] uppercase leading-[1.2]"; // H1: 36px, ALL CAPS, letter-spacing: 1.5px (0.094rem), line-height: 1.2
    case 2:
      return "font-heading font-normal text-[1.75rem] tracking-[0.063rem] uppercase leading-[1.3]"; // H2: 28px, ALL CAPS, letter-spacing: 1px (0.063rem), line-height: 1.3
    case 3:
      return "font-body font-bold text-xl leading-[1.4]"; // H3: 20px, bold, line-height: 1.4
    default:
      return "font-heading font-normal text-4xl tracking-[0.094rem] uppercase leading-[1.2]";
  }
}