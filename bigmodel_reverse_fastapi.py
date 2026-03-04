# -*- coding: utf-8 -*-
"""
BigModel 智谱AI 反向代理服务

基于浏览器Cookies的FastAPI反向代理服务，兼容OpenAI API格式。

功能：
- /v1/chat/completions: 聊天补全（支持流式/非流式）
- /v1/models: 模型列表
- /health: 健康检查
- Bearer Token 认证
- 完整的错误处理和日志记录

使用方式：
    python bigmodel_reverse_fastapi.py

配置：
    在 .env 文件中配置：
    - BIGMODEL_COOKIES: 浏览器Cookies（必需）
    - BIGMODEL_BASE_URL: BigModel站点URL（默认: https://bigmodel.cn）
    - BIGMODEL_CHAT_ENDPOINT: 聊天API端点（默认: /api/chat/completions）
    - BIGMODEL_MODELS_ENDPOINT: 模型列表API端点（默认: /api/models）
    - VALID_TOKENS: API访问Token列表（可选）
    - PORT: 服务端口（默认: 8000）
"""

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
from typing import Dict, Any, Generator, Union

# 加载环境变量
load_dotenv()


def setup_logging() -> logging.Logger:
    """
    配置日志系统

    创建日志目录，配置日志格式和处理器，
    返回配置好的日志记录器。

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(f'{log_dir}/bigmodel_fastapi.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 创建专用日志记录器
    logger = logging.getLogger('bigmodel_fastapi')
    logger.setLevel(logging.DEBUG)

    return logger


# 初始化日志
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
        # 尝试JSON数组格式
        VALID_TOKENS = json.loads(VALID_TOKENS_STR)
        logger.info(f"✅ 已加载 {len(VALID_TOKENS)} 个有效API Token（JSON格式）")
    except json.JSONDecodeError:
        # 如果不是JSON格式，尝试按逗号分隔
        VALID_TOKENS = [token.strip() for token in VALID_TOKENS_STR.split(',') if token.strip()]
        logger.info(f"✅ 已加载 {len(VALID_TOKENS)} 个有效API Token（逗号分隔）")
else:
    logger.warning("⚠️  未配置VALID_TOKENS，API将不进行鉴权验证（开发模式）")

# 服务器配置
PORT = int(os.environ.get("PORT", 8000))
DEBUG_STATUS = os.environ.get("DEBUG", "false").lower() == "true"


# ==================== 依赖函数 ====================

def verify_auth_token(authorization: str = Header(None)) -> Union[str, None]:
    """
    验证 Authorization Header 中的 Bearer Token

    Args:
        authorization: Authorization header，格式为 "Bearer <token>"

    Returns:
        验证通过的token字符串（如果无配置VALID_TOKENS则返回None）

    Raises:
        HTTPException: 鉴权失败时抛出401或403异常
    """
    # 如果未配置VALID_TOKENS，则跳过鉴权
    if not VALID_TOKENS:
        return None

    if not authorization:
        logger.warning("🔒 鉴权失败: 缺少Authorization Header")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization Header. Please provide a valid Bearer token."
        )

    # 解析Bearer token
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        logger.warning(f"🔒 鉴权失败: 无效的Authorization Scheme: {scheme}")
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization Scheme. Expected 'Bearer <token>'"
        )

    # 验证token是否在有效列表中
    if token not in VALID_TOKENS:
        logger.warning(f"🔒 鉴权失败: 无效或过期的token: {token[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid or Expired Token. Access denied."
        )

    logger.debug(f"✅ 鉴权成功: token {token[:10]}...")
    return token


# ==================== 初始化客户端 ====================

def init_bigmodel_client():
    """
    初始化BigModel客户端

    Returns:
        BigModelClient 或 None（初始化失败时）
    """
    try:
        # 延迟导入，避免循环依赖
        from bigmodel_client import BigModelClient

        client = BigModelClient(
            cookies=BIGMODEL_COOKIES,
            base_url=BIGMODEL_BASE_URL,
            chat_endpoint=BIGMODEL_CHAT_ENDPOINT,
            models_endpoint=BIGMODEL_MODELS_ENDPOINT
        )

        logger.info("✅ BigModel客户端初始化成功")
        logger.info(f"   Base URL: {BIGMODEL_BASE_URL}")
        logger.info(f"   Chat Endpoint: {BIGMODEL_CHAT_ENDPOINT}")
        logger.info(f"   Models Endpoint: {BIGMODEL_MODELS_ENDPOINT}")

        return client

    except ImportError as e:
        logger.error(f"❌ 导入BigModelClient失败: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ BigModel客户端初始化失败: {e}")
        return None


# 初始化客户端
bigmodel_client = init_bigmodel_client()


# ==================== FastAPI应用 ====================

app = FastAPI(
    title="BigModel Reverse API",
    description="基于浏览器Cookies的智谱AI反向代理服务，兼容OpenAI API格式",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API端点 ====================

@app.get("/")
async def root():
    """
    根端点 - 返回服务器信息

    Returns:
        Dict: 服务器信息字典
    """
    return {
        "name": "BigModel Reverse API",
        "version": "1.0.0",
        "description": "基于浏览器Cookies的智谱AI反向代理服务",
        "documentation": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """
    健康检查端点

    Returns:
        Dict: 健康状态和当前时间戳
    """
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "client_initialized": bigmodel_client is not None
    }


@app.get("/v1/models")
async def list_models():
    """
    获取可用模型列表

    Returns:
        Dict: 模型列表响应

    Raises:
        HTTPException: 客户端未初始化或请求失败时
    """
    if not bigmodel_client:
        raise HTTPException(
            status_code=500,
            detail="BigModel客户端未初始化，请检查配置文件"
        )

    try:
        result = bigmodel_client.list_models()
        logger.info("✅ 模型列表获取成功")
        return result
    except Exception as e:
        logger.error(f"❌ 获取模型列表失败: {e}")
        raise


@app.post("/v1/chat/completions")
async def chat_completions(
    request: dict,
    token: str = Depends(verify_auth_token)
):
    """
    聊天补全接口（兼容OpenAI API格式）

    支持流式和非流式响应，使用SSE格式传输流式数据。

    Args:
        request: OpenAI格式的请求体
            - model: 模型名称（可选，默认 glm-4）
            - messages: 消息列表（必需）
            - stream: 是否使用流式响应（可选，默认为False）
            - temperature: 温度参数（可选）
            - max_tokens: 最大生成长度（可选）

    Returns:
        StreamingResponse: 流式响应的SSE流
        JSONResponse: 非流式响应的JSON数据

    Raises:
        HTTPException: 认证失败或请求失败时
    """
    # 检查客户端是否初始化
    if not bigmodel_client:
        raise HTTPException(
            status_code=500,
            detail="BigModel客户端未初始化，请检查BIGMODEL_COOKIES配置"
        )

    # 检查Cookies是否配置
    if not BIGMODEL_COOKIES:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "未配置BIGMODEL_COOKIES，请在.env文件中配置从浏览器获取的Cookies",
                    "type": "authentication_error",
                    "code": "missing_credentials"
                }
            }
        )

    # 验证请求
    messages = request.get("messages", [])
    if not messages:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "messages字段不能为空",
                    "type": "invalid_request_error"
                }
            }
        )

    # 获取stream参数
    stream = request.get("stream", False)

    logger.info(f"📝 收到聊天请求，stream={stream}, messages_count={len(messages)}")

    try:
        # 调用客户端的聊天补全方法
        result = await bigmodel_client.chat_completions(request)

        if stream:
            # 流式响应
            logger.info("🔄 返回流式响应")
            return StreamingResponse(
                result,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式响应
            logger.info("📦 返回非流式响应")
            return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"❌ 聊天补全失败: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"聊天请求失败: {str(e)}",
                    "type": "server_error"
                }
            }
        )


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 启动 BigModel Reverse API 服务...")
    logger.info(f"📡 监听地址: http://0.0.0.0:{PORT}")
    logger.info(f"📖 API文档: http://localhost:{PORT}/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
