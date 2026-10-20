#!/usr/bin/env bash
# Exposes the local api + voice services to the internet via a cloudflared quick
# tunnel, so Twilio webhooks (voice, WhatsApp, SendGrid inbound/status) can reach
# them during local development. Run `pnpm tunnel` from the repo root.
#
# Requires `cloudflared` (https://github.com/cloudflare/cloudflared) on PATH.
# Copy the printed https://<random>.trycloudflare.com URL into PUBLIC_VOICE_URL /
# PUBLIC_API_URL in your .env and restart the affected service(s).
set -euo pipefail

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. See https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
  exit 1
fi

CADDY_URL="${CADDY_URL:-http://localhost:80}"

echo "Tunneling $CADDY_URL (routes /api/*, /voice/* via infra/Caddyfile) ..."
exec cloudflared tunnel --url "$CADDY_URL"
