# Action-Reaction Web Application

This is the Next.js 15 web frontend for the Action-Reaction automation platform. It follows the UI/UX specifications defined in `/docs/ui-ux-specs.md`.

## Features

- **Landing Page**: Modern, marketing-focused landing page with hero section, features showcase, and service integrations
- **Authentication**: Email/password and OAuth2 authentication (Google, GitHub)
- **Dashboard**: Main area management interface
- **Wizard**: Step-by-step automation creation flow
- **Service Connections**: OAuth2 service connection management
- **Execution History**: View logs of automation runs
- **Profile Management**: User account settings and activity logs

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the landing page.

## Pages & Routes

- `/` - Landing page (public, marketing-focused)
- `/auth` - Login/Registration page
- `/dashboard` - Main dashboard (requires authentication)
- `/wizard` - AREA creation wizard (requires authentication)
- `/connections` - Service connection management (requires authentication)
- `/history` - Execution logs (requires authentication)
- `/profile` - User profile and settings (requires authentication)

## Design System

This project implements the Action-Reaction design system:

### Typography
- **Headings**: Dela Gothic One (ALL CAPS with letter-spacing)
- **Body**: Inter
- **Monospace**: Roboto Mono

### Color Palette
- **Primary**: `#0052FF` (Main brand blue)
- **Accent**: `#FF4700` (High-visibility accent)
- **Secondary Accent**: `#00E0FF` (Code/tags highlight)
- **Success**: `#00C853`
- **Warning**: `#FFAB00`
- **Error**: `#D50000`

### Components
Built with Radix UI primitives and styled with Tailwind CSS for accessibility and consistency.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
