#!/bin/sh

# Create a placeholder APK file (actually a zip file with .apk extension)
echo "This is a placeholder APK file for the Action-Reaction mobile client." > /app/placeholder.txt
echo "Version: 1.0.0" >> /app/placeholder.txt
echo "Build Date: $(date)" >> /app/placeholder.txt

# Create a zip file and rename it as APK
cd /app
zip -r client.apk placeholder.txt

# Move the APK to the shared volume
mv client.apk /shared/

echo "Placeholder APK generated successfully at /shared/client.apk"