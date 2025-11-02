#!/bin/bash
set -e

GRADLE_PROPS="android/gradle.properties"

echo "Patching gradle.properties for Docker build..."

# Check if file exists
if [ ! -f "$GRADLE_PROPS" ]; then
    echo "Error: $GRADLE_PROPS not found. Run 'expo prebuild' first."
    exit 1
fi

# Backup original file
cp "$GRADLE_PROPS" "${GRADLE_PROPS}.bak"

# Apply patches for Docker/CI builds
echo "  - Increasing Gradle memory allocation"
sed -i 's/org.gradle.jvmargs=.*/org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=1024m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8/' "$GRADLE_PROPS"

echo "  - Disabling Gradle parallel execution (prevents daemon crashes)"
sed -i 's/org.gradle.parallel=.*/org.gradle.parallel=false/' "$GRADLE_PROPS"

echo "  - Disabling file system watching (fixes Docker polling issues)"
if ! grep -q "org.gradle.vfs.watch" "$GRADLE_PROPS"; then
    echo "org.gradle.vfs.watch=false" >> "$GRADLE_PROPS"
fi

if ! grep -q "org.gradle.daemon" "$GRADLE_PROPS"; then
    echo "org.gradle.daemon=true" >> "$GRADLE_PROPS"
fi

echo "  - Reducing to single architecture (arm64-v8a only)"
sed -i 's/reactNativeArchitectures=.*/reactNativeArchitectures=arm64-v8a/' "$GRADLE_PROPS"

echo "✓ gradle.properties patched successfully for Docker build"
