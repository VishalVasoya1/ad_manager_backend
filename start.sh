#!/bin/bash

APP_NAME="admanager-api"
PORT=8001

echo "🔍 Checking for existing container on port $PORT..."

# Find container using port
CONTAINER_ID=$(docker ps -q --filter "publish=$PORT")

if [ ! -z "$CONTAINER_ID" ]; then
  echo "⚠️ Container running on port $PORT. Stopping..."
  docker stop $CONTAINER_ID
  docker rm $CONTAINER_ID
fi

# Check if named container exists
EXISTING_CONTAINER=$(docker ps -a -q -f name=$APP_NAME)

if [ ! -z "$EXISTING_CONTAINER" ]; then
  echo "🗑 Removing existing container $APP_NAME..."
  docker rm -f $APP_NAME
fi

echo "🚀 Building and starting container..."
docker compose up --build -d

echo "✅ Application running on http://localhost:$PORT"