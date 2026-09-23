# =============================================================================
# Multi-stage Dockerfile for Smart Campus Service Frontend
# React + Vite + TypeScript
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Dependencies
# -----------------------------------------------------------------------------
FROM node:18-alpine as dependencies

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# -----------------------------------------------------------------------------
# Stage 2: Development Image
# -----------------------------------------------------------------------------
FROM node:18-alpine as development

WORKDIR /app

# Copy dependencies
COPY --from=dependencies /app/node_modules ./node_modules

# Copy package files
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies)
RUN npm install

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Development command with HMR
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# -----------------------------------------------------------------------------
# Stage 3: Builder (Build production assets)
# -----------------------------------------------------------------------------
FROM node:18-alpine as builder

WORKDIR /app

# Copy dependencies
COPY --from=dependencies /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build arguments for environment variables
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build for production
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 4: Production Image (Nginx)
# -----------------------------------------------------------------------------
FROM nginx:alpine as production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# -----------------------------------------------------------------------------
# Build Instructions:
# -----------------------------------------------------------------------------
# Development:
#   docker build --target development -t campus-frontend:dev .
#
# Production:
#   docker build --target production \
#     --build-arg VITE_API_BASE_URL=https://api.example.com \
#     -t campus-frontend:prod .
#
# For Cloud Run / Cloud Storage:
#   1. Build static files: docker build --target builder -o dist .
#   2. Deploy to Cloud Storage:
#      gsutil -m cp -r dist/* gs://BUCKET_NAME/
#   3. Set up Cloud CDN and Load Balancer
# -----------------------------------------------------------------------------
