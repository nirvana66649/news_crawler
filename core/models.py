from pydantic import BaseModel
from typing import List, Optional

class NewsSummaryItem(BaseModel):
    title: str       # 合并后的 summary 分类内容
    summary: str     # 所有 URL 拼接
    url: str         # 固定空字符串
    date: str        # summary_date

class PaginatedNewsSummary(BaseModel):
    items: List[NewsSummaryItem]
    total: int
    page: int
    page_size: int

class StandardResponse(BaseModel):
    code: int
    show: int
    msg: str
    data: PaginatedNewsSummary
