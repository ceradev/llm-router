FROM oven/bun:1-alpine

WORKDIR /app

COPY apps/web/package.json apps/web/bun.lock ./

RUN bun install --frozen-lockfile

COPY apps/web ./

RUN bun run build

FROM oven/bun:1-alpine

WORKDIR /app

COPY --from=0 /app/dist ./dist
COPY --from=0 /app/package.json ./

RUN bun install --frozen-lockfile

EXPOSE 4321

CMD ["bun", "x", "astro", "preview", "--host", "0.0.0.0", "--port", "4321"]
