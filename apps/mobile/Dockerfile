# Simple Dockerfile to run Expo for web preview inside a container
FROM node:20-alpine
WORKDIR /app

ENV EXPO_NO_TELEMETRY=1
ENV CI=1

COPY package.json package-lock.json ./
RUN npm ci --include=dev

COPY . .

EXPOSE 19006
CMD ["npm", "run", "web"]

