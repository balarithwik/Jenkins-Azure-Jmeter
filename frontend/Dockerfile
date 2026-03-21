FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY src ./src
RUN mkdir public && echo "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Retail App</title></head><body><div id='root'></div></body></html>" > public/index.html

EXPOSE 3000

CMD ["npm", "start"]