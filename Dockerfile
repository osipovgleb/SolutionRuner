FROM node:22-bookworm-slim AS dashboard-build

WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY config/ ./config/
RUN pip install --no-cache-dir -e .

COPY --from=dashboard-build /app/dashboard/dist ./dashboard/dist
EXPOSE 9999

CMD ["solution-runner-dashboard", "--host", "0.0.0.0", "--port", "9999", "--db", "/app/var/dashboard/dashboard.sqlite3", "--var", "/app/var", "--static", "/app/dashboard/dist"]
