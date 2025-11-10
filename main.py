"""新闻爬虫应用主入口文件"""
from api.routes.main import app
# uvicorn main:app --host 0.0.0.0 --port 8000 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)