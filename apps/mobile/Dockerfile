# Multi-stage Dockerfile for React Native + Expo APK build
# Force x86_64 architecture (required for Android SDK tools)
FROM --platform=linux/amd64 ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set versions to match local environment
ENV NODE_VERSION=20.18.1
ENV JAVA_VERSION=17
ENV ANDROID_SDK_VERSION=11076708
ENV ANDROID_API_LEVEL=36
ENV ANDROID_BUILD_TOOLS_VERSION=35.0.0
ENV ANDROID_NDK_VERSION=26.1.10909125

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    openjdk-${JAVA_VERSION}-jdk \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# Set up Android SDK
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/build-tools/${ANDROID_BUILD_TOOLS_VERSION}

RUN mkdir -p ${ANDROID_HOME}/cmdline-tools \
    && cd ${ANDROID_HOME}/cmdline-tools \
    && wget -q https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip \
    && unzip commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip \
    && rm commandlinetools-linux-${ANDROID_SDK_VERSION}_latest.zip \
    && mv cmdline-tools latest

# Accept Android SDK licenses and install required packages
RUN yes | ${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager --licenses || true
RUN ${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager \
    "platform-tools" \
    "platforms;android-${ANDROID_API_LEVEL}" \
    "build-tools;${ANDROID_BUILD_TOOLS_VERSION}" \
    "ndk;${ANDROID_NDK_VERSION}" \
    "cmake;3.22.1"

# Set working directory
WORKDIR /project

# Set environment variables for Gradle
ENV GRADLE_OPTS="-Xmx4096m -XX:MaxMetaspaceSize=1024m -XX:+HeapDumpOnOutOfMemoryError"
ENV JAVA_OPTS="-Xmx4096m"

# Create artifacts output directory
RUN mkdir -p /artifacts

# Default command (will be overridden by docker-compose)
CMD ["bash", "scripts/docker-build.sh"]
