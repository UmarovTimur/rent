FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/. .

ARG VITE_API_BASE_URL=/
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html/app
COPY landing/index.html /usr/share/nginx/html/
COPY landing/css/ /usr/share/nginx/html/css/
COPY landing/js/ /usr/share/nginx/html/js/
COPY landing/images/ /usr/share/nginx/html/images/

EXPOSE 80
