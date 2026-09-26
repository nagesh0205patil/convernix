#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
target="${1:-all}"
profile="${2:-production}"

if [[ ! -f .env ]]; then
  echo "Missing app/.env. Copy .env.example and set EXPO_PUBLIC_API_URL." >&2
  exit 1
fi
if ! grep -Eq '^EXPO_PUBLIC_API_URL=https://' .env && [[ "${ALLOW_INSECURE_BUILD:-false}" != "true" ]]; then
  echo "Production builds require an HTTPS EXPO_PUBLIC_API_URL." >&2
  exit 1
fi

case "$target" in
  apk) npx eas-cli build --platform android --profile preview ;;
  android) npx eas-cli build --platform android --profile "$profile" ;;
  ios) npx eas-cli build --platform ios --profile "$profile" ;;
  all) npx eas-cli build --platform all --profile "$profile" ;;
  *) echo "Usage: ./scripts/build.sh [apk|android|ios|all] [profile]" >&2; exit 2 ;;
esac
