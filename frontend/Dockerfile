FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# URLs de API accesibles desde el navegador (host:puerto mapeado en docker-compose)
ARG VITE_USERS_API=http://localhost:8001
ARG VITE_PRODUCT_API=http://localhost:8002
ARG VITE_OPTIMIZATION_API=http://localhost:8003
ENV VITE_USERS_API=$VITE_USERS_API
ENV VITE_PRODUCT_API=$VITE_PRODUCT_API
ENV VITE_OPTIMIZATION_API=$VITE_OPTIMIZATION_API

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
