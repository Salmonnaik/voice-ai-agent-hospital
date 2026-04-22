FROM node:20-slim

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Create models directory (model will be downloaded at runtime)
RUN mkdir -p models

EXPOSE 8080
CMD ["npm", "start"]
