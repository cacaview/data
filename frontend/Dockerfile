# --- Stage 1: builder ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps with reproducible lockfile
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Build production assets
COPY . .
RUN npm run build


# --- Stage 2: runtime (nginx) ---
FROM nginx:1.27-alpine

# Drop nginx's default user to a non-root
RUN sed -i 's|^user  nginx;|user  nginx;|' /etc/nginx/nginx.conf \
    && sed -i 's|listen       80;|listen       8080;|g' /etc/nginx/conf.d/default.conf

# Static assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config with API proxy + SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
