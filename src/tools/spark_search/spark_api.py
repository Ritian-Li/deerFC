# spark_search_tool.py

import os
import uuid
import json
import logging
import asyncio

import hashlib
import base64
import hmac
import time

from typing import Optional, Union, List, Dict
from urllib import parse
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import requests
import aiohttp
from langchain_core.callbacks.manager import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


class SparkSearchTool(BaseTool):
    """使用 Spark 聚合搜索 API 的 LangChain 工具类。"""

    name: str = "web_search"
    description: str = "使用讯飞 Spark 聚合搜索工具进行网络搜索"
    max_results: int = Field(default=5)
    api_key: str = Field(default_factory=lambda: os.getenv("SPARK_API_KEY", ""))
    api_secret: str = Field(default_factory=lambda: os.getenv("SPARK_API_SECRET", ""))
    app_id: str = Field(default_factory=lambda: os.getenv("SPARK_APP_ID", ""))

    @classmethod
    def from_api_key(
        cls, api_key: str, api_secret: str, app_id: str, max_results: int = max_results
    ):
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            app_id=app_id,
            max_results=max_results,
        )

    def _run(
        self,
        query: str,
        run_manager: Optional[object] = None,
    ) -> Union[str, List[Dict]]:
        try:
            if isinstance(query, dict):
                query = query["query"]
            print(f"🔍!!!当前搜索的问题：", query)
            return self._sync_search(query)
        except Exception as e:
            logger.error(f"Spark搜索出错: {str(e)}")
            return f"Spark搜索出错: {str(e)}"

    def invoke(self, input_text: str) -> Union[str, List[Dict]]:
        return self._run(input_text)

    def _sync_search(self, query: str) -> str:
        sid = hashlib.sha256(str(uuid.uuid4()).encode("utf-8")).hexdigest()[:16]
        url = self._build_auth_url(
            "https://cbm-search-api.cn-huabei-1.xf-yun.com/biz/search"
        )
        json_body = {
            "appId": self.app_id,
            "limit": self.max_results,
            "name": query,
            "pipeline_name": "pl_map_agg_search_biz",
            "sid": sid,
            "timestamp": int(time.time() * 1000),
            "uId": "uId",
            "open_rerank": True,
            "full_text": True,
            "disable_crawler": True,
            "disable_highlight": True,
        }

        headers = {"Content-Type": "application/json"}

        try:
            # 出网抖动时不设超时会挂起整个研究任务、占满并发槽
            response = requests.post(url, headers=headers, json=json_body, timeout=15)
            response_text = response.text
            if response.status_code != 200:
                logger.error(
                    f"Spark搜索API错误: {response.status_code}, {response_text}"
                )
                return f"Spark搜索API错误: {response.status_code}, {response_text}"

            result = response.json()
            # print(result)
            return self._format_results(query, result)
        except Exception as e:
            logger.exception("Spark搜索请求异常")
            return f"Spark搜索请求异常: {str(e)}"

    def _build_auth_url(self, request_url: str, method: str = "POST") -> str:
        url_result = parse.urlparse(request_url)
        date = format_date_time(mktime(datetime.now().timetuple()))
        signature_origin = f"host: {url_result.hostname}\ndate: {date}\n{method} {url_result.path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_base64 = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_base64}"'
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            "utf-8"
        )

        params = {
            "host": url_result.hostname,
            "date": date,
            "authorization": authorization,
        }

        return request_url + "?" + urlencode(params)

    def _format_results(self, query: str, result: Dict) -> str:
        hits = result.get("data", {}).get("documents", [])
        if not hits:
            return f"查询 '{query}' 没有找到结果"
        search_result = []
        for cont in hits:
            title = cont.get("name", "无标题")
            content = cont.get("summary", "没有内容")
            url = cont.get("url", "无URL")
            search_result.append({"title": title, "content": content, "url": url})

        return search_result
