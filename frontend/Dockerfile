FROM node:22-slim

WORKDIR /app

# Copy package files
COPY package.json .
COPY package-lock.json* .

RUN npm install

# Copy source code
COPY src src
COPY index.html .
COPY vite.config.js .

# Expose port
EXPOSE 5173

# Run dev server with HMR
CMD ["npm", "run", "dev"]
