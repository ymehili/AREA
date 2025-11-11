import { NextRequest, NextResponse } from 'next/server';

/**
 * GET /client.apk
 *
 * Redirects to the actual APK file location at /downloads/client.apk
 * This provides a cleaner, shorter URL for users to download the mobile app.
 */
export async function GET(request: NextRequest) {
  // Get the origin from the request
  const origin = request.nextUrl.origin;

  // Redirect to the static file
  return NextResponse.redirect(`${origin}/downloads/client.apk`, 301);
}
