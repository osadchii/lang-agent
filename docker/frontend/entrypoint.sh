#!/bin/sh
set -eu

# Fallback defaults for runtime configuration
: "${API_BASE_URL:=${VITE_API_BASE_URL:-http://localhost:8000/api}}"
: "${USER_ID:=${VITE_USER_ID:-1}}"
: "${USER_USERNAME:=${VITE_USER_USERNAME:-}}"
: "${USER_FIRST_NAME:=${VITE_USER_FIRST_NAME:-}}"
: "${USER_LAST_NAME:=${VITE_USER_LAST_NAME:-}}"

export API_BASE_URL USER_ID USER_USERNAME USER_FIRST_NAME USER_LAST_NAME

if [ -f /usr/share/nginx/html/runtime-config.js.template ]; then
  envsubst '$API_BASE_URL $USER_ID $USER_USERNAME $USER_FIRST_NAME $USER_LAST_NAME' \
    < /usr/share/nginx/html/runtime-config.js.template \
    > /usr/share/nginx/html/runtime-config.js
fi

exec "$@"
