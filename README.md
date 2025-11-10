# News Crawler System v2.0

An intelligent system for automated news crawling, summarization, and personalized delivery. It supports multi-user subscription management, task scheduling, and system monitoring.

## 🚀 Features

- **Automated Crawling**: Efficiently fetch news data with batch processing and retry mechanisms.
- **AI-Powered Summarization**: Generate concise summaries and categorize news using AI.
- **Personalized Delivery**: Schedule and deliver news content tailored to user preferences.
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
git clone <repository_url>
cd news_crawler
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the environment variable template
cp env.example .env

# Edit the configuration file
vim .env
```

### 5. Initialize the Database

Ensure the MySQL service is running and create the required database and tables.

### 6. Start the Application

```bash
# Development environment
python main.py

# Production environment
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Deploy n8n Workflow Automation

To deploy the n8n workflow automation system, you can use Docker. Refer to the official n8n repository for detailed instructions: [n8n GitHub Repository](https://github.com/n8n-io/n8n).

## 📁 Project Structure

```
news_crawler/
├── main.py              # Application entry point
├── core/                # Core modules (config, database, models, exceptions)
├── services/            # Business logic (crawling, monitoring, pushing, summarization)
├── n8n_workflow/        # Automated workflows for crawling
├── utils/               # Utility functions and logging
├── requirements.txt     # Dependency list
├── .env.example         # Environment variable template
└── README.md            # Project documentation
```

## 🔧 Configuration

### Database Configuration
- `DB_HOST`: Database host address
- `DB_PORT`: Database port
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_NAME`: Database name

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

### Health Check
```
GET /health
```

### System Metrics
```
GET /metrics?minutes=10
```

### Fetch User News
```
GET /crawl/news/{user_id}/subscriptions/news?page=1&page_size=10
```

### Manual Push
```
POST /admin/push_now
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

### Scheduled Delivery
- Daily delivery at 8:00 AM
- Supports manual trigger
- Tracks delivery status

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

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请创建 Issue 或联系维护团队。
