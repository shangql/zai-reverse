# 智谱AI (BigModel) 反向代理开发计划文档

## 一、项目概述

### 1.1 目标
基于现有千问（Qwen）逆向项目架构，为智谱AI（BigModel）实现FastAPI反向代理服务。

**核心特点**：
- ✅ **配置驱动** - 使用者自行提供cookies和其他参数
- ✅ **基于浏览器Cookies认证** - 使用bigmodel.cn站点的认证Cookies进行API调用
- ✅ **完全兼容 OpenAI API** - 支持流式/非流式响应
- 🚀 **高性能异步框架** - FastAPI + 自动API文档 (`/docs`)
- 🧠 **思维链支持** - 深度思考模式（reasoning_content）
- 🔐 **API鉴权** - Bearer Token认证（本地API访问控制）
- 📊 **配置管理** - 环境变量支持

**目标地址**：https://bigmodel.cn/trialcenter/modeltrial/text

---

## 二、技术架构

### 2.1 项目结构

```
zai-reverse/
├── bigmodel_reverse_fastapi.py    # 主程序（新建）
├── bigmodel_client.py             # BigModel浏览器客户端封装（新建）
├── requirements.txt               # 依赖包（更新）
├── .env.example                   # 环境变量模板（更新）
├── .env                           # 本地配置（新建）
├── docs/
│   └── BIGMODEL_DEVELOPMENT_PLAN.md  # 本文档
└── README_BIGMODEL.md             # 使用文档（新建）
```

### 2.2 技术栈
- **Web框架**: FastAPI >= 0.116.1
- **ASGI服务器**: uvicorn >= 0.35.0
- **HTTP客户端**: requests >= 2.32.4
- **配置管理**: python-dotenv >= 1.1.1
- **数据验证**: pydantic >= 2.8.2
- **文件上传**: python-multipart >= 0.0.6

### 2.3 API端点设计

| 端点 | 方法 | 说明 | 鉴权 |
|------|------|------|------|
| `/` | GET | 服务器信息 | ❌ |
| `/health` | GET | 健康检查 | ❌ |
| `/docs` | GET | Swagger UI 文档 | ❌ |
| `/v1/models` | GET | 列出可用模型 | ❌ |
| `/v1/chat/completions` | POST | 聊天补全（兼容OpenAI） | ✅ |

---

## 三、使用者配置指南

### 3.1 必需配置项

使用者在 `.env` 文件中需提供以下配置：

```bash
# ==================== 必需配置 ====================

# BigModel 浏览器Cookies（从浏览器Network标签页获取）
BIGMODEL_COOKIES="your_browser_cookies_here"

# BigModel 站点基础URL（通常是 https://bigmodel.cn）
BIGMODEL_BASE_URL="https://bigmodel.cn"

# ==================== 可选配置 ====================

# 聊天API端点（默认值: /api/chat/completions）
BIGMODEL_CHAT_ENDPOINT="/api/chat/completions"

# 模型列表API端点（默认值: /api/models）
BIGMODEL_MODELS_ENDPOINT="/api/models"

# 用户信息API端点（默认值: /api/user/info）
BIGMODEL_USER_ENDPOINT="/api/user/info"

# ==================== 本地API鉴权 ====================

# API鉴权Token列表（用于本地API访问控制）
VALID_TOKENS=["sk-token1", "sk-token2"]

# ==================== 服务器配置 ====================

PORT=8000
DEBUG=true
```

### 3.2 使用者需从浏览器获取的信息

**步骤**：
1. 访问 https://bigmodel.cn/trialcenter/modeltrial/text 并登录
2. 打开 F12 → Network 标签页
3. 发送一条测试消息
4. 找到聊天API请求（通常是 `chat/completions`）
5. 复制以下信息：
   - **Request Headers** 中的 `Cookie` 值 → `BIGMODEL_COOKIES`
   - **Request Headers** 中的关键信息（User-Agent、Origin等）
   - **Request URL** 中的路径部分 → `BIGMODEL_CHAT_ENDPOINT`
6. 如有需要，查看 `/api/models` 请求获取模型列表端点

---

## 四、详细开发计划

### 阶段一：Cookie管理器（bigmodel_client.py）

#### 任务1.1：创建CookieManager类

```python
class CookieManager:
    """
    Cookie管理器 - 解析和验证使用者配置的Cookies
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
        """解析Cookie字符串为字典"""
        cookies = {}
        if cookie_string:
            for item in cookie_string.split(';'):
                if '=' in item.strip():
                    key, value = item.strip().split('=', 1)
                    cookies[key.strip()] = value.strip()
        return cookies

    def get_cookie_string(self) -> str:
        """返回原始Cookie字符串"""
        return self.raw_cookie_string

    def get(self, key: str, default: str = "") -> str:
        """获取指定Cookie值"""
        return self.cookies.get(key, default)

    def get_all(self) -> Dict[str, str]:
        """获取所有Cookies"""
        return self.cookies.copy()

    def validate(self) -> Dict[str, Any]:
        """验证Cookie完整性（可选，由使用者自行确保有效性）"""
        return {
            'has_cookies': len(self.cookies) > 0,
            'cookie_count': len(self.cookies),
            'keys': list(self.cookies.keys())
        }
```

---

### 阶段二：BigModel客户端（bigmodel_client.py）

#### 任务2.1：创建BigModelClient类

```python
class BigModelClient:
    """
    用于与 bigmodel.cn Web界面 API 交互的客户端。
    使用使用者配置的Cookies进行认证和API调用。
    """

    def __init__(
        self,
        cookies: str = "",
        base_url: str = "https://bigmodel.cn",
        chat_endpoint: str = "/api/chat/completions",
        models_endpoint: str = "/api/models",
        user_endpoint: str = "/api/user/info"
    ):
        """
        初始化BigModel客户端

        Args:
            cookies: 使用者提供的浏览器Cookies字符串
            base_url: BigModel站点基础URL
            chat_endpoint: 聊天补全API端点
            models_endpoint: 模型列表API端点
            user_endpoint: 用户信息API端点
        """
        self.cookies = cookies
        self.base_url = base_url.rstrip('/')
        self.chat_endpoint = chat_endpoint
        self.models_endpoint = models_endpoint
        self.user_endpoint = user_endpoint

        # 初始化会话
        self.session = requests.Session()

        # 初始化Cookie管理器
        self.cookie_manager = CookieManager(cookies)

        # 设置Cookies到会话
        cookie_string = self.cookie_manager.get_cookie_string()
        if cookie_string:
            # 解析并设置cookies
            self.session.headers.update({"Cookie": cookie_string})

        # 初始化请求头（模拟真实浏览器环境）
        self._init_headers()

    def _init_headers(self):
        """初始化请求头，模拟真实浏览器环境"""
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json; charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "origin": self.base_url,
            "referer": f"{self.base_url}/trialcenter/modeltrial/text",
        })

    def list_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        url = f"{self.base_url}{self.models_endpoint}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=500,
                detail={"error": {"message": f"获取模型列表失败: {str(e)}"}}
            )

    async def chat_completions(self, openai_request: dict) -> Union[Dict, Generator]:
        """
        执行聊天补全，模拟OpenAI API

        Args:
            openai_request: OpenAI格式的请求

        Returns:
            非流式响应: dict
            流式响应: Generator
        """
        # 解析OpenAI请求
        model = openai_request.get("model", "glm-4")
        messages = openai_request.get("messages", [])
        stream = openai_request.get("stream", False)

        # 构建BigModel请求
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

        if stream:
            return self._streaming_response(request_body, model)
        else:
            return self._non_streaming_response(request_body, model)

    def _streaming_response(self, request: dict, original_model: str) -> Generator:
        """处理SSE流式响应"""
        url = f"{self.base_url}{self.chat_endpoint}"

        # 确保Cookie随请求发送
        cookie_string = self.cookie_manager.get_cookie_string()
        headers = {"Cookie": cookie_string}

        with self.session.post(url, json=request, headers=headers, stream=True) as response:
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
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

    def _non_streaming_response(self, request: dict, original_model: str) -> Dict:
        """处理非流式响应"""
        url = f"{self.base_url}{self.chat_endpoint}"

        # 确保Cookie随请求发送
        cookie_string = self.cookie_manager.get_cookie_string()
        headers = {"Cookie": cookie_string}

        response_text = ""
        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

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
        """将BigModel响应转换为OpenAI格式"""
        # 默认转换逻辑（使用者可能需要根据实际响应调整）
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": original_model,
            "choices": [{
                "index": 0,
                "delta": data.get("content", ""),
                "finish_reason": data.get("finish_reason")
            }]
        }

    def _extract_content(self, data: dict, current_text: str) -> str:
        """从BigModel响应中提取内容"""
        # 默认提取逻辑（使用者可能需要根据实际响应调整）
        if "content" in data:
            return current_text + data["content"]
        return current_text
```

---

### 阶段三：FastAPI服务（bigmodel_reverse_fastapi.py）

#### 任务3.1：创建主程序

```python
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import json
import os
import logging
import sys
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Generator, Union

# 加载环境变量
load_dotenv()

# 配置日志
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{log_dir}/bigmodel_fastapi.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger('bigmodel_fastapi')

logger = setup_logging()

# ==================== 配置区域 ====================

# BigModel配置（从环境变量读取）
BIGMODEL_COOKIES = os.environ.get("BIGMODEL_COOKIES", "")
BIGMODEL_BASE_URL = os.environ.get("BIGMODEL_BASE_URL", "https://bigmodel.cn")
BIGMODEL_CHAT_ENDPOINT = os.environ.get("BIGMODEL_CHAT_ENDPOINT", "/api/chat/completions")
BIGMODEL_MODELS_ENDPOINT = os.environ.get("BIGMODEL_MODELS_ENDPOINT", "/api/models")

# API鉴权配置
VALID_TOKENS_STR = os.environ.get("VALID_TOKENS", "")
VALID_TOKENS = []
if VALID_TOKENS_STR:
    try:
        VALID_TOKENS = json.loads(VALID_TOKENS_STR)
    except json.JSONDecodeError:
        VALID_TOKENS = [token.strip() for token in VALID_TOKENS_STR.split(',') if token.strip()]

# 服务器配置
PORT = int(os.environ.get("PORT", 8000))
DEBUG_STATUS = os.environ.get("DEBUG", "false").lower() == "true"

# ==================== 初始化客户端 ====================

from bigmodel_client import BigModelClient

# 创建BigModel客户端实例
try:
    bigmodel_client = BigModelClient(
        cookies=BIGMODEL_COOKIES,
        base_url=BIGMODEL_BASE_URL,
        chat_endpoint=BIGMODEL_CHAT_ENDPOINT,
        models_endpoint=BIGMODEL_MODELS_ENDPOINT
    )
    logger.info("✅ BigModel客户端初始化成功")
except Exception as e:
    logger.error(f"❌ BigModel客户端初始化失败: {e}")
    bigmodel_client = None

# ==================== FastAPI应用 ====================

app = FastAPI(
    title="BigModel Reverse API",
    description="基于浏览器Cookies的智谱AI反向代理服务，兼容OpenAI API格式",
    version="1.0.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 依赖注入 ====================

def verify_auth_token(authorization: str = Header(None)):
    """验证Authorization Header中的Bearer Token"""
    if not VALID_TOKENS:
        return None

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token not in VALID_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid or Expired Token")

    return token

# ==================== API端点 ====================

@app.get("/")
async def root():
    """服务器信息"""
    return {
        "name": "BigModel Reverse API",
        "version": "1.0.0",
        "description": "基于浏览器Cookies的智谱AI反向代理服务",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "timestamp": int(time.time())}

@app.get("/v1/models")
async def list_models():
    """获取可用模型列表"""
    if not bigmodel_client:
        raise HTTPException(status_code=500, detail="BigModel客户端未初始化")
    return bigmodel_client.list_models()

@app.post("/v1/chat/completions")
async def chat_completions(request: dict, token: str = Depends(verify_auth_token)):
    """
    聊天补全接口（兼容OpenAI API格式）

    请求示例：
    {
        "model": "glm-4",
        "messages": [{"role": "user", "content": "你好"}],
        "stream": false
    }
    """
    if not bigmodel_client:
        raise HTTPException(status_code=500, detail="BigModel客户端未初始化")

    if not BIGMODEL_COOKIES:
        raise HTTPException(
            status_code=401,
            detail="未配置BIGMODEL_COOKIES，请在.env文件中配置"
        )

    stream = request.get("stream", False)

    try:
        result = await bigmodel_client.chat_completions(request)

        if stream:
            return StreamingResponse(result, media_type="text/event-stream")
        else:
            return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"聊天补全失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 启动服务 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
```

---

## 五、实现步骤

### 步骤1：创建bigmodel_client.py
- [x] 实现CookieManager类
- [x] 实现BigModelClient类
- [x] 实现流式/非流式响应处理
- [x] 实现OpenAI格式转换

### 步骤2：创建bigmodel_reverse_fastapi.py
- [x] 实现FastAPI应用
- [x] 实现API鉴权
- [x] 实现/v1/models端点
- [x] 实现/v1/chat/completions端点
- [x] 实现健康检查

### 步骤3：更新配置文件
- [x] 更新.env.example
- [x] 验证requirements.txt（无需更新）

### 步骤4：创建使用文档
- [x] 创建README_BIGMODEL.md
- [x] 添加使用示例
- [x] 添加故障排除指南

---

## 六、使用示例

### 6.1 环境配置

```bash
# .env 文件内容
BIGMODEL_COOKIES="your_browser_cookies_here"
BIGMODEL_BASE_URL="https://bigmodel.cn"
BIGMODEL_CHAT_ENDPOINT="/api/chat/completions"
BIGMODEL_MODELS_ENDPOINT="/api/models"
VALID_TOKENS=["sk-test-token"]
PORT=8000
DEBUG=true
```

### 6.2 启动服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python bigmodel_reverse_fastapi.py
```

### 6.3 API调用

```bash
# 基础聊天（非流式）
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 流式响应
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'
```

---

## 七、参考

- [现有千问逆向项目源码](./qwen_reverse_fastapi.py)
- [OpenAI API文档](https://platform.openai.com/docs/api-reference/chat)

---

*文档版本: 3.0*
*创建日期: 2026-01-30*
*基于现有千问逆向项目架构*
*核心变更：配置驱动，使用者自行提供Cookies和API端点信息*
