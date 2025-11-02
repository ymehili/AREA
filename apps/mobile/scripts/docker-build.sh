#!/bin/bash
set -e

echo "=========================================="
echo "Starting React Native + Expo APK build"
echo "=========================================="

# Initialize git to avoid Expo warning (changes won't be persisted)
echo "Initializing git repository..."
git config --global user.email "docker@area.build"
git config --global user.name "Docker Builder"
git init
git add .
git commit -m "Initial commit for build" || true

# Install npm dependencies
echo "Installing npm dependencies..."
npm install --legacy-peer-deps

# Clean android directory manually to avoid EBUSY errors with Docker volumes
echo "Cleaning Android build directories..."
rm -rf android/.gradle android/app/build android/build || true

# Run Expo prebuild to generate native Android project (CI mode for non-interactive)
echo "Running Expo prebuild..."
CI=1 npx expo prebuild --platform android

# Patch gradle.properties for Docker build optimizations
echo "Applying Docker-specific patches to gradle.properties..."
bash scripts/patch-gradle-properties.sh

# Generate local.properties for Android SDK location
echo "Generating local.properties..."
echo "sdk.dir=${ANDROID_SDK_ROOT}" > android/local.properties

# Navigate to Android directory
cd android

# Make gradlew executable
chmod +x ./gradlew

# Clean previous builds
echo "Cleaning previous builds..."
./gradlew clean

# Build release APK
echo "Building release APK..."
./gradlew assembleRelease

# Copy APK to artifacts directory
echo "Copying APK to artifacts..."
APK_SOURCE="app/build/outputs/apk/release/app-release.apk"
APK_DEST="/artifacts/app-release.apk"

if [ -f "$APK_SOURCE" ]; then
    cp "$APK_SOURCE" "$APK_DEST"
    echo "=========================================="
    echo "Build successful!"
    echo "APK location: /artifacts/app-release.apk"
    echo "=========================================="
    ls -lh "$APK_DEST"
else
    echo "ERROR: APK not found at $APK_SOURCE"
    exit 1
fi

# Optional: Build debug APK if needed
# echo "Building debug APK..."
# ./gradlew assembleDebug
# cp app/build/outputs/apk/debug/app-debug.apk /artifacts/app-debug.apk

echo "Build process completed!"
