# -*- coding: utf-8 -*-
"""
BigModel 智谱AI 浏览器客户端封装

用于与 bigmodel.cn Web界面 API 交互的客户端。
使用使用者配置的Cookies进行认证和API调用。

功能：
- Cookie管理：解析和验证使用者配置的Cookies
- API调用：聊天补全、模型列表等
- 流式响应：支持SSE流式响应处理
- 格式转换：将BigModel响应转换为OpenAI格式

使用方式：
    client = BigModelClient(
        cookies="your_browser_cookies_here",
        base_url="https://bigmodel.cn",
        chat_endpoint="/api/chat/completions",
        models_endpoint="/api/models"
    )
    result = await client.chat_completions({
        "model": "glm-4",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": False
    })
"""

import requests
import json
import time
from typing import Dict, Any, Generator, Union, Optional


class CookieManager:
    """
    Cookie管理器 - 解析和验证使用者配置的Cookies

    功能：
    - 将 "key1=value1; key2=value2" 格式的Cookie字符串解析为字典
    - 提供便捷的Cookie获取方法
    - 验证Cookie是否配置
    """

    def __init__(self, cookie_string: str = ""):
        """
        初始化Cookie管理器

        Args:
            cookie_string: 使用者提供的Cookie字符串，格式如 "key1=value1; key2=value2"
        """
        self.cookies = self._parse_cookies(cookie_string)
        self.raw_cookie_string = cookie_string

    def _parse_cookies(self, cookie_string: str) -> Dict[str, str]:
        """
        解析Cookie字符串为字典

        Args:
            cookie_string: "key1=value1; key2=value2" 格式的Cookie字符串

        Returns:
            Dict: 解析后的Cookie字典
        """
        cookies = {}
        if cookie_string:
            for item in cookie_string.split(';'):
                if '=' in item.strip():
                    key, value = item.strip().split('=', 1)
                    cookies[key.strip()] = value.strip()
        return cookies

    def get_cookie_string(self) -> str:
        """
        返回原始Cookie字符串

        Returns:
            str: 原始Cookie字符串
        """
        return self.raw_cookie_string

    def get(self, key: str, default: str = "") -> str:
        """
        获取指定Cookie值

        Args:
            key: Cookie名称
            default: 如果Cookie不存在返回的默认值

        Returns:
            str: Cookie值或默认值
        """
        return self.cookies.get(key, default)

    def get_all(self) -> Dict[str, str]:
        """
        获取所有Cookies的副本

        Returns:
            Dict: 所有Cookies的字典副本
        """
        return self.cookies.copy()

    def validate(self) -> Dict[str, Any]:
        """
        验证Cookie完整性

        Returns:
            Dict: 包含验证结果的字典
                - has_cookies: 是否有Cookie配置
                - cookie_count: Cookie数量
                - keys: Cookie键列表
        """
        return {
            'has_cookies': len(self.cookies) > 0,
            'cookie_count': len(self.cookies),
            'keys': list(self.cookies.keys())
        }


class BigModelClient:
    """
    用于与 bigmodel.cn Web界面 API 交互的客户端。

    功能：
    - 使用浏览器Cookies进行认证
    - 支持聊天补全API（流式/非流式）
    - 支持获取模型列表
    - 自动将BigModel响应转换为OpenAI兼容格式

    使用者需要从浏览器获取：
    - BIGMODEL_COOKIES: 完整的Cookie字符串
    - BIGMODEL_CHAT_ENDPOINT: 聊天API端点路径
    - BIGMODEL_MODELS_ENDPOINT: 模型列表API端点路径
    """

    def __init__(
        self,
        cookies: str = "",
        base_url: str = "https://bigmodel.cn",
        chat_endpoint: str = "/api/chat/completions",
        models_endpoint: str = "/api/models"
    ):
        """
        初始化BigModel客户端

        Args:
            cookies: 使用者提供的浏览器Cookies字符串
            base_url: BigModel站点基础URL
            chat_endpoint: 聊天补全API端点
            models_endpoint: 模型列表API端点
        """
        self.cookies = cookies
        self.base_url = base_url.rstrip('/')
        self.chat_endpoint = chat_endpoint
        self.models_endpoint = models_endpoint

        # 初始化会话
        self.session = requests.Session()

        # 初始化Cookie管理器
        self.cookie_manager = CookieManager(cookies)

        # 初始化请求头（模拟真实浏览器环境）
        self._init_headers()

    def _init_headers(self):
        """
        初始化请求头，模拟真实浏览器环境

        设置必要的请求头，包括：
        - Accept: 接受JSON和纯文本响应
        - Content-Type: JSON内容类型
        - User-Agent: 浏览器标识
        - Origin: 源站（用于CORS）
        - Referer: 来源页面（部分API需要）
        """
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json; charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "origin": self.base_url,
            "referer": f"{self.base_url}/trialcenter/modeltrial/text",
        })

    def list_models(self) -> Dict[str, Any]:
        """
        获取可用模型列表

        Returns:
            Dict: 模型列表响应（JSON格式）

        Raises:
            Exception: 请求失败时抛出异常
        """
        url = f"{self.base_url}{self.models_endpoint}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取模型列表失败: {str(e)}")

    async def chat_completions(self, openai_request: dict) -> Union[Dict, Generator]:
        """
        执行聊天补全，模拟OpenAI API

        Args:
            openai_request: OpenAI格式的请求字典，包含：
                - model: 模型名称
                - messages: 消息列表
                - stream: 是否使用流式响应（可选，默认为False）
                - temperature: 温度参数（可选）
                - top_p: Top-P参数（可选）
                - max_tokens: 最大生成长度（可选）

        Returns:
            Union[Dict, Generator]:
                - 非流式响应: 完整的JSON字典
                - 流式响应: 生成器，产出SSE格式的数据块

        Examples:
            # 非流式调用
            result = await client.chat_completions({
                "model": "glm-4",
                "messages": [{"role": "user", "content": "你好"}],
                "stream": False
            })

            # 流式调用
            async for chunk in client.chat_completions({
                "model": "glm-4",
                "messages": [{"role": "user", "content": "讲个笑话"}],
                "stream": True
            }):
                print(chunk)
        """
        # 解析OpenAI请求
        model = openai_request.get("model", "glm-4")
        messages = openai_request.get("messages", [])
        stream = openai_request.get("stream", False)

        # 构建BigModel请求体
        request_body = {
            "model": model,
            "messages": messages,
            "stream": True  # 始终使用流式获取实时数据
        }

        # 复制可选参数
        optional_params = ['temperature', 'top_p', 'max_tokens']
        for param in optional_params:
            if param in openai_request:
                request_body[param] = openai_request[param]

        # 根据stream参数选择响应方式
        if stream:
            return self._streaming_response(request_body, model)
        else:
            return self._non_streaming_response(request_body, model)

    def _streaming_response(self, request: dict, original_model: str) -> Generator:
        """
        处理SSE流式响应

        Args:
            request: 请求体字典
            original_model: 原始模型名称（用于响应中）

        Yields:
            str: SSE格式的数据块，如 "data: {...}\n\n"
        """
        url = f"{self.base_url}{self.chat_endpoint}"

        # 确保Cookie随请求发送
        cookie_string = self.cookie_manager.get_cookie_string()
        headers = {"Cookie": cookie_string}

        try:
            with self.session.post(url, json=request, headers=headers, stream=True) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    # 检查SSE前缀
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break

                        try:
                            data = json.loads(data_str)
                            openai_chunk = self._convert_to_openai_chunk(data, original_model)
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            # 请求失败时发送错误块
            error_chunk = {
                "id": f"chatcmpl-error-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": original_model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"Error: {str(e)}"},
                    "finish_reason": "error"
                }]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE}\n\n"

    def _non_streaming_response(self, request: dict, original_model: str) -> Dict:
        """
        处理非流式响应

        通过流式请求获取数据，但聚合所有响应后返回完整的JSON。

        Args:
            request: 请求体字典
            original_model: 原始模型名称（用于响应中）

        Returns:
            Dict: OpenAI格式的完整响应
        """
        url = f"{self.base_url}{self.chat_endpoint}"

        # 确保Cookie随请求发送
        cookie_string = self.cookie_manager.get_cookie_string()
        headers = {"Cookie": cookie_string}

        response_text = ""
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            with self.session.post(url, json=request, headers=headers, stream=True) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            response_text = self._extract_content(data, response_text)
                            usage_data = data.get("usage", usage_data)
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            raise Exception(f"聊天请求失败: {str(e)}")

        # 构建OpenAI格式的响应
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": original_model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": usage_data
        }

    def _convert_to_openai_chunk(self, data: dict, original_model: str) -> Dict:
        """
        将BigModel流式响应转换为OpenAI格式

        Args:
            data: BigModel响应数据
            original_model: 原始模型名称

        Returns:
            Dict: OpenAI格式的响应块
        """
        # 默认转换逻辑
        # 根据实际BigModel响应格式可能需要调整
        content = data.get("content", "")
        if isinstance(content, dict):
            # 如果content是字典，尝试提取文本内容
            content = str(content)

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": original_model,
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": data.get("finish_reason")
            }]
        }

    def _extract_content(self, data: dict, current_text: str) -> str:
        """
        从BigModel响应中提取内容并累积

        Args:
            data: BigModel响应数据
            current_text: 当前已累积的文本

        Returns:
            str: 更新后的累积文本
        """
        # 默认提取逻辑
        # 根据实际BigModel响应格式可能需要调整
        content = data.get("content", "")
        if isinstance(content, str):
            return current_text + content
        elif isinstance(content, dict):
            # 如果content是字典，尝试提取text字段
            return current_text + str(content)
        return current_text
