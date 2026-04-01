# ---------- BUILD ----------
FROM oven/bun:1-alpine AS builder

WORKDIR /app

# instalar deps
COPY apps/web/package.json apps/web/bun.lock ./
RUN bun install --frozen-lockfile

# copiar código
COPY apps/web .

# build astro
RUN bun run build

# ---------- PRODUCTION ----------
FROM oven/bun:1-alpine

WORKDIR /app

# instalar servidor estático
RUN bun add -g serve

# copiar build final
COPY --from=builder /app/dist ./dist

EXPOSE 4321

CMD ["serve", "-s", "dist", "-l", "4321"]