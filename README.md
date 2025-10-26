# BTC Accumulation Bot 🤖

An automated Bitcoin accumulation bot that uses the BTCMarkets API to implement a smart DCA (Dollar Cost Averaging) strategy with dynamic purchase amounts based on market conditions.

## Features ✨

- **Smart DCA Strategy**: Adjusts purchase amounts based on:
  - Mayer Multiple (200-day moving average)
  - Fear & Greed Index
  - Market conditions analysis
- **Real-time Market Analysis**: 
  - Price monitoring
  - Technical indicators
  - Market sentiment tracking
- **Secure API Integration**: 
  - BTCMarkets API v3 compliant
  - Secure credential handling
  - Robust error management
- **Comprehensive Logging**:
  - Detailed execution logs
  - Portfolio tracking
  - Performance metrics
- **Advanced Deployment Tools**:
  - Easy EC2 deployment
  - Environment validation
  - Log exploration utilities

### Installation 🚀

1. Clone the repository:
```bash
git clone https://github.com/dbose/btc-bots.git
cd btc-bots
```

2. Create and configure environment variables
```bash
cp .env.example .env
# Edit .env with your BTCMarkets API credentials and settings
```
3. Install dependencies:
```bash
pip install requests numpy python-dotenv
```

### Configuration ⚙️
Configure the bot by editing .env:
```
AWS_EC2_PUBLIC_IP=your_ec2_public_ip  # Replace with your EC2 public IP

# BTCMarkets API Credentials
BTCMARKETS_API_KEY=your_api_key
BTCMARKETS_PRIVATE_KEY=your_private_key

# Trading Settings  
BASE_WEEKLY_AMOUNT=500
MAX_WEEKLY_AMOUNT=2000
MIN_WEEKLY_AMOUNT=100
```
For EC2 deployment, ensure the following config variables are set in `deploy.py`:
```
KEY_PATH = "..../btc-bot-key.pem"  # Replace with your instance private key path
REMOTE_PATH = "/home/ec2-user/btc-bot"
```

### Deployment 📦
Deploy to EC2 using the deployment script:
```bash
python deploy.py deploy  # Deploy bot
python deploy.py test   # Test execution
python deploy.py check  # Verify environment
```

### Log Management 📊
Explore bot activity using various log commands
```bash
python deploy.py logs today      # View today's log
python deploy.py logs live       # Live log viewer
python deploy.py logs stats      # View statistics
python deploy.py logs portfolio  # View portfolio progress
```

### Configuration for GitHub Actions 🤖& Scheduling ⏰

- AWS_ACCESS_KEY_ID: AWS access key
- AWS_SECRET_ACCESS_KEY: AWS secret key
- EC2_INSTANCE_ID: EC2 instance ID
- EC2_PUBLIC_IP: EC2 public IP address
- S3_BUCKET_NAME: S3 bucket name for logs
- BTCMARKETS_API_KEY: BTCMarkets API key
- BTCMARKETS_PRIVATE_KEY: BTCMarkets private key
- BASE_WEEKLY_AMOUNT: Base weekly purchase amount
- MAX_WEEKLY_AMOUNT: Maximum weekly amount
- MIN_WEEKLY_AMOUNT: Minimum weekly amount
