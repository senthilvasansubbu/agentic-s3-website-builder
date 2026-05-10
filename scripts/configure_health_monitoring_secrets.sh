#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Configure repository secrets used by continuous health monitoring.

Usage:
  scripts/configure_health_monitoring_secrets.sh [--qa-url URL] [--prod-url URL]

Examples:
  scripts/configure_health_monitoring_secrets.sh --qa-url https://qa.example.com --prod-url https://app.example.com
  scripts/configure_health_monitoring_secrets.sh --qa-url https://qa.example.com

Notes:
- Requires authenticated GitHub CLI (gh auth status)
- Sets repo secrets: QA_HEALTH_URL and/or PROD_HEALTH_URL
- Continuous monitor workflow auto-starts once corresponding secrets are set
EOF
}

qa_url=""
prod_url=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --qa-url)
      qa_url="${2:-}"
      shift 2
      ;;
    --prod-url)
      prod_url="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$qa_url" && -z "$prod_url" ]]; then
  echo "Provide at least one URL via --qa-url or --prod-url." >&2
  usage
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required but not found." >&2
  exit 1
fi

if [[ -n "$qa_url" ]]; then
  gh secret set QA_HEALTH_URL --body "$qa_url"
  echo "Set QA_HEALTH_URL"
fi

if [[ -n "$prod_url" ]]; then
  gh secret set PROD_HEALTH_URL --body "$prod_url"
  echo "Set PROD_HEALTH_URL"
fi

echo "Done. Continuous health monitor will use configured environment secrets automatically."
