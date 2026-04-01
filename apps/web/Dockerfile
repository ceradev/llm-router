FROM oven/bun:1-alpine AS builder

WORKDIR /app

# 👇 build args (clave)
ARG PUBLIC_API_BASE_URL
ENV PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

# 👇 debug opcional
# RUN echo "API BASE: $PUBLIC_API_BASE_URL"

RUN bun run build


# ---------- production ----------
FROM oven/bun:1-alpine

WORKDIR /app

RUN bun add -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 4321

CMD ["serve", "-s", "dist", "-l", "4321"]