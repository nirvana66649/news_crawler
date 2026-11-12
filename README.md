# News Crawler System v2.0

An intelligent system for automated news crawling and summarization. It supports multi-user subscription management, task scheduling, and system monitoring.

## 🚀 Features

- **Automated Crawling**: Efficiently fetch news data with batch processing and retry mechanisms.
- **AI-Powered Summarization**: Generate concise summaries and categorize news using AI.
- **System Monitoring**: Real-time performance and health monitoring.
- **RESTful API**: Comprehensive API for seamless integration.
- **Configuration Management**: Centralized configuration with environment variable support.
- **Structured Logging**: Detailed logs for debugging and error tracking.
- **Database Optimization**: Connection pooling and query optimization.

## 📋 System Requirements

- Python 3.8+
- MySQL 5.7+
- Minimum 2GB RAM
- Minimum 10GB disk space

## 🛠️ Installation and Deployment

### 1. Clone the Repository

```bash
git clone https://github.com/nirvana66649/news_crawler.git
cd news_crawler
```

### 2. Create a Virtual Environment

Use Python 3.8+ (`python3` on macOS/Linux). Python 3.12 is recommended.

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The repository ships `.env.example` only. Copy it to a local `.env` (this file is gitignored and must not be committed):

```bash
cp .env.example .env
```

Then edit `.env` and set at least `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE`, and `CRAWLER_WEBHOOK_URL`.

### 5. Initialize the Database

Start MySQL 5.7+, then create the application database (name must match `DB_DATABASE` in `.env`, default `news`):

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS news CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

News CRUD endpoints need the existing application tables. If MySQL is not running, startup logs a warning and continues. The root endpoint (`GET /`) can still be used to confirm the API process is up.

### 6. Start the Application

```bash
# Development environment
python main.py

# Optional: run dependency / config / DB checks first
python start.py

# Production environment
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API listens on `http://localhost:8000`.

### 7. Verify the Setup

```bash
curl -i http://localhost:8000/
```

A successful start returns **HTTP 200 OK** with a JSON body similar to:

```json
{"message": "新闻爬虫系统", "version": "2.0.0", "status": "running"}
```

### 8. Deploy n8n Workflow Automation (optional)

To deploy the n8n workflow automation system, you can use Docker. Import `n8n_workflow/crawler.json` and `n8n_workflow/RESTful API.json`, then point `CRAWLER_WEBHOOK_URL` at the webhook. Refer to the official n8n repository for detailed instructions: [n8n GitHub Repository](https://github.com/n8n-io/n8n).

## 📁 Project Structure

```
news_crawler/
├── main.py              # Application entry point
├── start.py             # Preflight checks, then start uvicorn
├── api/                 # FastAPI routes
├── core/                # Core modules (config, database, models, exceptions)
├── services/            # Business logic (crawling, monitoring, summarization)
├── n8n_workflow/        # Automated workflows for crawling
├── utils/               # Utility functions and logging
├── requirements.txt     # Dependency list
├── .env.example         # Environment variable template (copy to .env)
├── .gitignore
└── README.md            # Project documentation
```

## 🔧 Configuration

### Database Configuration
- `DB_HOST`: Database host address
- `DB_PORT`: Database port
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name (this is the variable the app reads; not `DB_NAME`)

### Crawler Configuration
- `CRAWLER_WEBHOOK_URL`: API endpoint for the crawler
- `CRAWLER_TIMEOUT`: Request timeout (seconds)
- `CRAWLER_BATCH_SIZE`: Batch size for processing
- `CRAWLER_BATCH_DELAY`: Delay between batches (seconds)

### Application Configuration
- `APP_DEBUG`: Debug mode
- `APP_LOG_LEVEL`: Log level
- `APP_TIMEZONE`: Timezone setting

## 📊 API Endpoints

### 增删改查(control by n8n workflow6)
```
post /news/update
post /news/subscribe
post /news/delete
get /news/search
```


### Fetch User News
```
GET /crawl/news/{user_id}/subscriptions/news?page=1&page_size=10
```

### Manual Crawl and Summarize
```
POST /crawl_and_summarize
Content-Type: application/json

{
    "subscription_id": "123"
}
```

## 📈 Monitoring and Logging

### System Monitoring
- CPU usage
- Memory usage
- Disk space
- Database connections

### Logging
- Console and file logging
- Colored log output
- Structured log format
- Automatic log rotation

### Health Check Thresholds
- CPU Warning: 70%, Critical: 85%
- Memory Warning: 80%, Critical: 90%
- Disk Warning: 80%, Critical: 90%

## 🔄 Task Scheduling

### Automated Crawling
- Executes every 24 hours
- Retries failed subscriptions
- Batch processing to prevent overload

## 🛡️ Security Features

- Input validation
- SQL injection prevention
- Exception handling and recovery
- Connection pooling to prevent leaks

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Failure**
   - Verify the database service is running
   - Check connection parameters
   - Ensure network connectivity

2. **Crawler Timeout**
   - Adjust `CRAWLER_TIMEOUT`
   - Check target API availability
   - Monitor network conditions

3. **High Memory Usage**
   - Adjust batch size
   - Review database connection pooling
   - Monitor long-running tasks

### Viewing Logs
```bash
# 查看实时日志
tail -f logs/news_crawler_*.log

# 搜索错误日志
grep "ERROR" logs/news_crawler_*.log
```

