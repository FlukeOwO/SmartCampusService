# =============================================================================
# Smart Campus Frontend - multi-stage image
#   development : Vite dev server + hot reload (docker compose)
#   production  : static build served by nginx (local prod test)
# บน cloud ไม่ใช้ image นี้: frontend-cd build แล้วอัปโหลดไป Cloud Storage
#
# Vite 8 ต้องใช้ Node 20.19+ หรือ 22.12+
# =============================================================================
ARG NODE_VERSION=22

# -----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
# ต้องมี devDependencies (vite, plugin-react) ทั้งตอน dev และตอน build
RUN npm ci && npm cache clean --force

# -----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS development
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# -----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# -----------------------------------------------------------------------------
FROM nginx:alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
