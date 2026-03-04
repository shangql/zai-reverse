# BigModel 智谱AI 反向代理

基于 **FastAPI** 框架，通过浏览器Cookies认证，为智谱AI（BigModel）站点提供OpenAI兼容的本地API服务。

## 核心特性

- ✅ **配置驱动** - 使用者自行提供Cookies和API端点
- ✅ **完全兼容 OpenAI API** - 支持流式/非流式响应
- 🚀 **高性能异步框架** - FastAPI + 自动API文档 (`/docs`)
- 🔐 **可选API鉴权** - Bearer Token认证
- 📊 **完整日志记录** - 便于问题排查

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# BigModel 浏览器Cookies（必需）
# 从浏览器Network标签页获取
BIGMODEL_COOKIES="your_browser_cookies_here"

# BigModel 站点基础URL
BIGMODEL_BASE_URL="https://bigmodel.cn"

# 聊天API端点（根据实际请求填写）
BIGMODEL_CHAT_ENDPOINT="/api/chat/completions"

# 模型列表API端点
BIGMODEL_MODELS_ENDPOINT="/api/models"

# API鉴权Token（可选）
VALID_TOKENS=["sk-your-token"]

# 服务端口
PORT=8000
```

### 3. 获取BigModel Cookies

**步骤**：
1. 访问 https://bigmodel.cn/trialcenter/modeltrial/text 并登录
2. 打开 F12 → Network 标签页
3. 发送一条测试消息
4. 找到 `chat/completions` 请求
5. 复制 Request Headers 中的完整 Cookie 值

### 4. 启动服务

```bash
# 直接运行
python bigmodel_reverse_fastapi.py

# 或使用 Uvicorn
uvicorn bigmodel_reverse_fastapi:app --host 0.0.0.0 --port 8000
```

### 5. 验证服务

访问 API 文档：http://localhost:8000/docs

## API端点

| 端点 | 方法 | 说明 | 鉴权 |
|------|------|------|------|
| `/` | GET | 服务器信息 | ❌ |
| `/health` | GET | 健康检查 | ❌ |
| `/docs` | GET | Swagger UI 文档 | ❌ |
| `/v1/models` | GET | 列出可用模型 | ❌ |
| `/v1/chat/completions` | POST | 聊天补全（兼容OpenAI） | ✅ |

## 使用示例

### 基础聊天

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 流式响应

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## 项目结构

```
zai-reverse/
├── bigmodel_reverse_fastapi.py  # FastAPI主程序
├── bigmodel_client.py           # BigModel客户端封装
├── requirements.txt             # Python依赖
├── .env.example                 # 环境变量模板
├── .env                         # 本地配置（创建此文件）
├── README_BIGMODEL.md           # 本文档
└── logs/                        # 日志目录（启动后自动创建）
```

## 故障排除

### Cookie过期

**现象**：API返回401错误
**解决**：重新获取Cookie（参考"快速开始"中的步骤）

### 鉴权失败

**现象**：403错误
**解决**：
- 检查 `VALID_TOKENS` 配置
- 确认请求头格式：`Authorization: Bearer sk-token`
- 查看日志确认Token加载状态

### 服务无法启动

```bash
# 查看日志
cat logs/bigmodel_fastapi.log

# 检查依赖
pip install -r requirements.txt
```

## 许可证

MIT License
