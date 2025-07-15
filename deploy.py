#!/usr/bin/env python3
"""
Enhanced deployment script for BTC bot with advanced log exploration
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
EC2_IP = "ec2-44-204-146-74.compute-1.amazonaws.com"  # Replace with your IP
KEY_PATH = "//btc-bot-key.pem"  # Replace with your key path
REMOTE_PATH = "/home/ec2-user/btc-bot"

def run_command(cmd, description, capture_output=True):
    """Run shell command with nice output"""
    print(f"🔄 {description}...")
    try:
        if capture_output:
            result = subprocess.run(cmd,
                                    shell=True,
                                    check=True,
                                    capture_output=True,
                                    text=True)
            if result.stdout:
                print(result.stdout)
            return True
        else:
            # For interactive commands like tail -f
            result = subprocess.run(cmd, shell=True, check=True)
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr if capture_output else str(e)}")
        return False


def deploy_bot():
    """Deploy bot to EC2"""
    print("🚀 Deploying BTC Bot to EC2...")

    # Check if files exist
    if not Path("btc_bot.py").exists():
        print("❌ btc_bot.py not found in current directory!")
        return False

    # Upload main bot file
    upload_cmd = f'scp -i "{KEY_PATH}" btc_bot.py ec2-user@{EC2_IP}:{REMOTE_PATH}/'
    if not run_command(upload_cmd, "Uploading btc_bot.py"):
        return False

    # Upload env file
    upload_cmd = f'scp -i "{KEY_PATH}" .env ec2-user@{EC2_IP}:{REMOTE_PATH}/'
    if not run_command(upload_cmd, "Uploading .env"):
        return False

    # Upload any config files
    if Path("config").exists():
        config_cmd = f'scp -i "{KEY_PATH}" -r config/ ec2-user@{EC2_IP}:{REMOTE_PATH}/'
        run_command(config_cmd, "Uploading config files")

    # Upload scripts if they exist
    if Path("scripts").exists():
        scripts_cmd = f'scp -i "{KEY_PATH}" -r scripts/ ec2-user@{EC2_IP}:{REMOTE_PATH}/'
        run_command(scripts_cmd, "Uploading scripts")

    # Test syntax on remote server
    test_cmd = f'ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "cd {REMOTE_PATH} && python3 -m py_compile btc_bot.py"'
    if not run_command(test_cmd, "Testing syntax on remote server"):
        return False

    print("🎉 Deployment successful!")
    print(f"📡 Bot is ready on {EC2_IP}")
    return True


def test_bot():
    """Test bot execution on remote server with environment loading"""
    print("🧪 Testing bot execution...")

    # Use the secure script that loads environment variables
    test_cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}

        # Check if secure script exists
        if [ -f scripts/run_bot_secure.sh ]; then
            echo '🔐 Using secure execution script...'
            ./scripts/run_bot_secure.sh
        elif [ -f .env ]; then
            echo '🔐 Loading environment and running bot...'
            export \\$(grep -v '^#' .env | grep -v '^\\$' | xargs)
            python3 btc_bot.py
        else
            echo '❌ No .env file found and no secure script available'
            echo 'Please ensure .env file exists in {REMOTE_PATH}'
            exit 1
        fi
    "'''

    if run_command(test_cmd, "Running bot test"):
        print("✅ Bot test successful! Check the logs for details.")
    else:
        print("❌ Bot test failed - check the logs")


def check_environment():
    """Check if environment is properly configured on remote server"""
    print("🔍 Checking remote environment configuration...")

    check_cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}
        echo '=== ENVIRONMENT CHECK ==='

        # Check if .env file exists
        if [ -f .env ]; then
            echo '✅ .env file found'
            echo '📊 Environment variables in .env:'
            grep -v '^#' .env | grep -v '^\\$' | cut -d'=' -f1 | sed 's/^/  - /'
        else
            echo '❌ .env file not found'
        fi

        echo ''
        echo '=== BOT FILE CHECK ==='
        if [ -f btc_bot.py ]; then
            echo '✅ Bot file found'
            echo 'Last modified:' \\$(stat -c %y btc_bot.py)
        else
            echo '❌ Bot file not found'
        fi
    "'''

    run_command(check_cmd, "Checking environment configuration")


def view_logs(subcommand=None):
    """Enhanced log viewing with multiple options"""

    if not subcommand:
        print("""
📄 Log Exploration Options:

Usage: python deploy.py logs <option>

Options:
    today       - View today's log (last 50 lines)
    live        - View live log (follow mode)
    yesterday   - View yesterday's log
    week        - View last 7 days of logs
    all         - List all available log files
    search      - Search logs for specific terms
    errors      - Show only error messages
    purchases   - Show only successful purchases
    portfolio   - Show portfolio summaries
    stats       - Show execution statistics
    tail <n>    - Show last N lines of today's log

Examples:
    python deploy.py logs today
    python deploy.py logs live
    python deploy.py logs search "PERFECT STORM"
    python deploy.py logs tail 100
        """)
        return

    if subcommand == "today":
        view_today_log()
    elif subcommand == "live":
        view_live_log()
    elif subcommand == "yesterday":
        view_yesterday_log()
    elif subcommand == "week":
        view_week_logs()
    elif subcommand == "all":
        list_all_logs()
    elif subcommand == "search":
        search_logs()
    elif subcommand == "errors":
        view_errors()
    elif subcommand == "purchases":
        view_purchases()
    elif subcommand == "portfolio":
        view_portfolio_summaries()
    elif subcommand == "stats":
        view_stats()
    elif subcommand == "tail":
        view_tail_log()
    else:
        print(f"❌ Unknown log option: {subcommand}")
        view_logs()  # Show help


def view_today_log():
    """View today's log"""
    print("📄 Fetching today's log...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        LOG_FILE={REMOTE_PATH}/logs/btc_bot_\\$(date +%Y%m%d).log
        if [ -f \\$LOG_FILE ]; then
            tail -50 \\$LOG_FILE
        else
            echo '❌ No log file found for today'
            echo 'Available logs:'
            ls -la {REMOTE_PATH}/logs/ | tail -5
        fi
    "'''

    run_command(cmd, "Fetching today's log")


def view_live_log():
    """View live log with follow mode"""
    print("👀 Starting live log viewer... (Press Ctrl+C to exit)")
    print("=" * 50)

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        LOG_FILE={REMOTE_PATH}/logs/btc_bot_\\$(date +%Y%m%d).log
        if [ -f \\$LOG_FILE ]; then
            echo 'Following live log: '\\$LOG_FILE
            echo '=================================='
            tail -f \\$LOG_FILE
        else
            echo '❌ No log file found for today'
            echo 'Creating empty log file and watching...'
            touch \\$LOG_FILE
            tail -f \\$LOG_FILE
        fi
    "'''

    run_command(cmd, "Starting live log viewer", capture_output=False)


def view_yesterday_log():
    """View yesterday's log"""
    print("📄 Fetching yesterday's log...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        YESTERDAY=\\$(date -d 'yesterday' +%Y%m%d)
        LOG_FILE={REMOTE_PATH}/logs/btc_bot_\\$YESTERDAY.log
        if [ -f \\$LOG_FILE ]; then
            echo '=== YESTERDAY\\'S LOG ('\\$YESTERDAY') ==='
            cat \\$LOG_FILE
        else
            echo '❌ No log file found for yesterday'
        fi
    "'''

    run_command(cmd, "Fetching yesterday's log")


def view_week_logs():
    """View last 7 days of logs"""
    print("📅 Fetching last 7 days of logs...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        echo '=== LAST 7 DAYS OF BOT ACTIVITY ==='
        cd {REMOTE_PATH}/logs
        for i in {{6..0}}; do
            DATE=\\$(date -d \\"\\$i days ago\\" +%Y%m%d)
            LOG_FILE=btc_bot_\\$DATE.log
            if [ -f \\$LOG_FILE ]; then
                echo ''
                echo '--- '\\$(date -d \\"\\$i days ago\\" +%Y-%m-%d)' ---'
                grep -E '(Starting BTC|PERFECT STORM|EXTREME|UNDERSOLD|OVERBOUGHT|PURCHASE SUCCESSFUL|PURCHASE FAILED|CRITICAL ERROR)' \\$LOG_FILE 2>/dev/null || echo 'No activity'
            fi
        done
    "'''

    run_command(cmd, "Fetching weekly activity summary")


def list_all_logs():
    """List all available log files"""
    print("📋 Listing all available log files...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== ALL LOG FILES ==='
        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            ls -lah btc_bot_*.log | while read line; do
                filename=\\$(echo \\$line | awk '{{print \\$9}}')
                size=\\$(echo \\$line | awk '{{print \\$5}}')
                date=\\$(echo \\$line | awk '{{print \\$6, \\$7, \\$8}}')
                echo \\\"📄 \\$filename (\\$size) - \\$date\\\"
            done
        else
            echo '❌ No log files found'
        fi

        echo ''
        echo '=== DISK USAGE ==='
        du -sh . 2>/dev/null || echo 'Could not calculate disk usage'
    "'''

    run_command(cmd, "Listing all log files")


def search_logs():
    """Search logs for specific terms"""
    if len(sys.argv) < 4:
        search_term = input("🔍 Enter search term: ")
    else:
        search_term = sys.argv[3]

    print(f"🔍 Searching logs for: '{search_term}'")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== SEARCH RESULTS FOR: {search_term} ==='

        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            grep -n -i '{search_term}' btc_bot_*.log 2>/dev/null | head -20 | while IFS=':' read file line content; do
                echo \\\"📄 \\$file [Line \\$line]: \\$content\\\"
            done

            echo ''
            echo '=== SUMMARY ==='
            total_matches=\\$(grep -i '{search_term}' btc_bot_*.log 2>/dev/null | wc -l)
            echo \\\"Found \\$total_matches matches across log files\\\"
        else
            echo '❌ No log files found'
        fi
    "'''

    run_command(cmd, f"Searching for '{search_term}'")


def view_errors():
    """Show only error messages from logs"""
    print("🚨 Fetching error messages from logs...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== ERROR MESSAGES ==='

        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            grep -n -E '(ERROR|FAILED|❌|🚨)' btc_bot_*.log 2>/dev/null | tail -20 | while IFS=':' read file line content; do
                echo \\\"🚨 \\$file [Line \\$line]: \\$content\\\"
            done
        else
            echo '❌ No log files found'
        fi
    "'''

    run_command(cmd, "Fetching error messages")


def view_purchases():
    """Show only successful purchases"""
    print("💰 Fetching successful purchases from logs...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== SUCCESSFUL PURCHASES ==='

        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            grep -A 5 -B 1 'PURCHASE SUCCESSFUL' btc_bot_*.log 2>/dev/null | grep -E '(PURCHASE SUCCESSFUL|Purchased:|Amount:|Price:|Order ID:)' | while read line; do
                echo \\\"💰 \\$line\\\"
            done

            echo ''
            echo '=== PURCHASE SUMMARY ==='
            total_purchases=\\$(grep 'PURCHASE SUCCESSFUL' btc_bot_*.log 2>/dev/null | wc -l)
            echo \\\"Total successful purchases: \\$total_purchases\\\"
        else
            echo '❌ No log files found'
        fi
    "'''

    run_command(cmd, "Fetching purchase history")


def view_portfolio_summaries():
    """Show portfolio summaries from logs"""
    print("📊 Fetching portfolio summaries from logs...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== PORTFOLIO PROGRESSION ==='

        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            # Get the most recent portfolio summary from each day
            for logfile in \\$(ls btc_bot_*.log 2>/dev/null | sort); do
                date_from_file=\\$(echo \\$logfile | sed 's/btc_bot_\\(.*\\)\\.log/\\1/')
                formatted_date=\\$(echo \\$date_from_file | sed 's/\\(....\\)\\(..\\)\\(..\\)/\\1-\\2-\\3/')

                portfolio=\\$(grep -A 4 'FINAL PORTFOLIO SUMMARY' \\$logfile 2>/dev/null | tail -4)
                if [ -n \\"\\$portfolio\\" ]; then
                    echo \\\"\\\"
                    echo \\"📅 \\$formatted_date:\\"
                    echo \\"\\$portfolio\\" | sed 's/^/    /'
                fi
            done
        else
            echo '❌ No log files found'
        fi
    "'''

    run_command(cmd, "Fetching portfolio progression")


def view_stats():
    """Show execution statistics"""
    print("📈 Calculating bot execution statistics...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        cd {REMOTE_PATH}/logs
        echo '=== BOT EXECUTION STATISTICS ==='

        if [ \\$(ls -1 btc_bot_*.log 2>/dev/null | wc -l) -gt 0 ]; then
            total_executions=\\$(grep 'Starting BTC Accumulation Bot' btc_bot_*.log 2>/dev/null | wc -l)
            successful_purchases=\\$(grep 'PURCHASE SUCCESSFUL' btc_bot_*.log 2>/dev/null | wc -l)
            failed_purchases=\\$(grep 'PURCHASE FAILED' btc_bot_*.log 2>/dev/null | wc -l)
            no_action_days=\\$(grep 'NO PURCHASE TODAY' btc_bot_*.log 2>/dev/null | wc -l)

            echo \\"📊 Total Executions: \\$total_executions\\"
            echo \\"✅ Successful Purchases: \\$successful_purchases\\"
            echo \\"❌ Failed Purchases: \\$failed_purchases\\"
            echo \\"⏸️  No Action Days: \\$no_action_days\\"

            if [ \\$total_executions -gt 0 ]; then
                success_rate=\\$(echo \\"scale=1; \\$successful_purchases * 100 / \\$total_executions\\" | bc -l 2>/dev/null || echo 'N/A')
                echo \\"📈 Purchase Rate: \\$success_rate%\\"
            fi

            echo \\\"\\\"
            echo \\"=== STRATEGY SIGNALS (Last 30 days) ===\\"
            grep -o -E '(PERFECT STORM|EXTREME OVERSOLD|UNDERSOLD|OVERBOUGHT|EXTREME BUBBLE)' btc_bot_*.log 2>/dev/null | sort | uniq -c | sort -nr | while read count signal; do
                echo \\"📊 \\$signal: \\$count times\\"
            done

            echo \\\"\\\"
            echo \\"=== RECENT ACTIVITY ===\\"
            tail -1 btc_bot_*.log 2>/dev/null | grep 'Bot execution completed' | wc -l | xargs echo \\"Last successful completion: \\" executions

        else
            echo '❌ No log files found'
        fi
    "'''

    run_command(cmd, "Calculating statistics")


def view_tail_log():
    """View last N lines of today's log"""
    if len(sys.argv) < 4:
        lines = input("📄 Number of lines to show (default 100): ") or "100"
    else:
        lines = sys.argv[3]

    try:
        lines = int(lines)
    except ValueError:
        print("❌ Invalid number of lines")
        return

    print(f"📄 Fetching last {lines} lines of today's log...")

    cmd = f'''ssh -i "{KEY_PATH}" ec2-user@{EC2_IP} "
        LOG_FILE={REMOTE_PATH}/logs/btc_bot_\\$(date +%Y%m%d).log
        if [ -f \\$LOG_FILE ]; then
            tail -{lines} \\$LOG_FILE
        else
            echo '❌ No log file found for today'
        fi
    "'''

    run_command(cmd, f"Fetching last {lines} lines")


def ssh_connect():
    """Open SSH connection"""
    print("🔗 Opening SSH connection...")
    ssh_cmd = f'ssh -i "{KEY_PATH}" ec2-user@{EC2_IP}'
    os.system(ssh_cmd)


def show_help():
    """Show help message"""
    print("""
🤖 BTC Bot Deployment & Management Tool

Usage: python deploy.py <command> [options]

Commands:
    deploy      - Upload bot to EC2 and test syntax
    test        - Run bot test execution
    logs        - Enhanced log exploration (see logs help)
    ssh         - Open SSH connection to server

Log Commands:
    logs                   - Show log options help
    logs today             - View today's log (last 50 lines)  
    logs live              - View live log (follow mode)
    logs yesterday         - View yesterday's complete log
    logs week              - View last 7 days activity summary
    logs all               - List all available log files
    logs search <term>     - Search logs for specific terms
    logs errors            - Show only error messages
    logs purchases         - Show only successful purchases
    logs portfolio         - Show portfolio progression over time
    logs stats             - Show execution statistics
    logs tail <n>          - Show last N lines of today's log

Examples:
    python deploy.py deploy
    python deploy.py logs today
    python deploy.py logs live
    python deploy.py logs search "PERFECT STORM"
    python deploy.py logs tail 200
    python deploy.py logs stats
    """)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "deploy":
        deploy_bot()
    elif command == "test":
        test_bot()
    elif command == "check":
        check_environment()
    elif command == "logs":
        subcommand = sys.argv[2] if len(sys.argv) > 2 else None
        view_logs(subcommand)
    elif command == "ssh":
        ssh_connect()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()