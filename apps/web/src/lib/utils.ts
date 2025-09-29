import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Utility function to apply heading styles according to the specs
export function headingClasses(level: 1 | 2 | 3 = 1): string {
  switch(level) {
    case 1:
      return "font-heading font-normal text-[36px] tracking-[1.5px] uppercase"; // H1: 36px, ALL CAPS, letter-spacing: 1.5px
    case 2:
      return "font-heading font-normal text-[28px] tracking-[1px] uppercase"; // H2: 28px, ALL CAPS, letter-spacing: 1px
    case 3:
      return "font-bold text-[20px]"; // H3: 20px, bold
    default:
      return "font-heading font-normal text-[36px] tracking-[1.5px] uppercase";
  }
}