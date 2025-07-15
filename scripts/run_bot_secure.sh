#!/bin/bash
# Secure bot execution script

set -e  # Exit on any error

BOT_DIR="/home/ec2-user/btc-bot"
ENV_FILE="$BOT_DIR/.env"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Environment file not found: $ENV_FILE"
    echo "Please create .env file with required variables"
    exit 1
fi

# Load environment variables
echo "🔐 Loading environment variables..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Validate required variables
required_vars=("BTCMARKETS_API_KEY" "BTCMARKETS_API_SECRET")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

echo "✅ Environment variables loaded successfully"

# Execute bot
cd "$BOT_DIR"
python3 btc_bot.py

# Clear sensitive variables from memory
unset BTCMARKETS_API_KEY BTCMARKETS_API_SECRET