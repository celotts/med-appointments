FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/package.json ./
RUN npm install --production

COPY --from=builder /app/build ./build

EXPOSE 3000

CMD ["npx", "serve", "-s", "build", "-l", "3000"]
