# Build context is the monorepo ROOT (see infra/docker-compose.yml), because this
# is a pnpm workspace member and needs the root workspace + lockfile.

FROM node:22-alpine AS base
RUN corepack enable
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN pnpm install --frozen-lockfile=false

# ---- dev: used by docker-compose.dev.yml for live reload ----
FROM deps AS dev
COPY . .
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "dev"]

# ---- builder: production build ----
FROM deps AS builder
COPY . .
RUN pnpm --filter web run build

# ---- runner: production runtime ----
FROM base AS runner
ENV NODE_ENV=production
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["node", "server.js"]
