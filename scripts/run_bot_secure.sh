#!/bin/bash

# Source environment variables
set -a
source ../.env
set +a

# Run bot with DRY_RUN flag support
if [ "$DRY_RUN" = "1" ]; then
    echo "🔬 Running in dry-run mode..."
    python3 -c "
import btc_bot
bot = btc_bot.BTCAccumulationBot(dry_run=True)
bot.run()
"
else
    python3 ../btc_bot.py
fi

# Clear sensitive variables
unset BTCMARKETS_API_KEY BTCMARKETS_PRIVATE_KEY