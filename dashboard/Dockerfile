# =============================================================================
# Web dashboard — Online Assessment Monitoring System
#
# Stage 1 builds the React app with Vite; stage 2 serves the static files
# with nginx. The production build talks to the live Firebase project
# (baandod-testing), see src/firebase.ts. See docs/DOCKER.md.
# =============================================================================
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
