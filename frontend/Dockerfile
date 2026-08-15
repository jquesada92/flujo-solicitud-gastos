FROM node:22-alpine AS build
ARG VITE_TIME_ZONE=America/Panama
ENV VITE_TIME_ZONE=${VITE_TIME_ZONE}
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
