#!/bin/sh
set -e

echo "Starting web server entrypoint..."

# Check if APK exists in shared volume and copy it to public/downloads
if [ -f "/apk-shared/app-release.apk" ]; then
    echo "Found APK in shared volume, copying to public/downloads/client.apk..."
    cp /apk-shared/app-release.apk /app/public/downloads/client.apk
    echo "APK copied successfully ($(du -h /app/public/downloads/client.apk | cut -f1))"
else
    echo "Warning: No APK found in shared volume at /apk-shared/app-release.apk"
    echo "The mobile app download will not be available."
fi

# Execute the command passed to docker run
echo "Starting Next.js server..."
exec "$@"
