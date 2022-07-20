FROM node:16.16-alpine
WORKDIR /react
COPY package.json package.json
RUN npm install
COPY . .
RUN npm run build
