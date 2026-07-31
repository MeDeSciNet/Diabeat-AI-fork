# Builds one of the two frontends and serves the static output.
# The terminology lint runs as part of `npm run build`, so a build that would
# ship forbidden wording fails here rather than in review (PRD 7.2).
ARG APP=care-web

FROM node:22-alpine AS build
ARG APP
WORKDIR /repo

COPY package.json package-lock.json* ./
COPY packages/web-shared/package.json packages/web-shared/
COPY packages/care-web/package.json packages/care-web/
COPY packages/station-web/package.json packages/station-web/
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY packages/shared-schemas/generated packages/shared-schemas/generated
COPY packages/web-shared packages/web-shared
COPY packages/care-web packages/care-web
COPY packages/station-web packages/station-web

ARG VITE_API_BASE=http://localhost:8000
ARG VITE_PAM_BASE=http://localhost:8100
ARG VITE_API_TOKEN=dev-token
ENV VITE_API_BASE=$VITE_API_BASE VITE_PAM_BASE=$VITE_PAM_BASE VITE_API_TOKEN=$VITE_API_TOKEN

RUN npm run build --workspace @somno/${APP}

FROM nginx:1.27-alpine
ARG APP
COPY --from=build /repo/packages/${APP}/dist /usr/share/nginx/html
COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
