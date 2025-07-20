# --- build stage --------------------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build         # crée .next/standalone + .next/static

# --- run stage ----------------------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app

# 1. Copier le serveur standalone (il inclut server.js et node_modules minifiés)
COPY --from=builder /app/.next/standalone ./

# 2. Copier les assets publics
COPY --from=builder /app/public ./public

# 3. Copier les fichiers statiques générés
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
