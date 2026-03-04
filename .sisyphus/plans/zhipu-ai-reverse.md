# 智谱AI (BigModel) 反向代理服务开发执行计划 (增强版)

## TL;DR

> **快速总结**: 基于现有的 `qwen_reverse_fastapi.py` 架构，为智谱AI官方API (v4) 构建一个高效、兼容OpenAI协议的反向代理服务，支持流式输出、深度思考模式（思维链）及多模态输入。
> 
> **交付物**:
> - `bigmodel_client.py`: 核心客户端类，处理 API 调用与响应转换。
> - `bigmodel_reverse_fastapi.py`: FastAPI 服务端，提供 OpenAI 兼容接口。
> - `README_BIGMODEL.md`: 项目使用与配置指南。
> - 更新 `.env.example` 与 `requirements.txt`。
> 
> **估计工作量**: 中等 (Medium)
> **并行执行**: 是 - 3 个 Wave
> **关键路径**: `bigmodel_client.py` 基础框架 -> 核心对话逻辑实现 -> FastAPI 集成验证

---

## 上下文

### 原始请求
用户希望参考现有千问逆向项目的架构，为智谱AI实现反向代理，支持官方 V4 API 的全部特性（流式、思维链、多模态）。

### 调研摘要
**关键讨论**:
- 采用三层架构模式：FastAPI 路由 -> 业务转换层 -> 官方 API 协议层。
- 认证使用 Bearer Token (API Key)。
- 思维链通过 `reasoning_content` 字段处理，需在流式响应中精准提取。

**调研发现**:
- 智谱 V4 API 接口（`/chat/completions`）与 OpenAI 高度兼容。
- 启用深度思考需在请求体中添加 `enable_thinking: true`。
- 模型映射需要覆盖 GLM-4 及其变体（flash, plus, voice, vision 等）。

### 缺口分析 (Gap Analysis)
- **思维链提取**: 需确保在流式 SSE 解析中，`reasoning_content` 能够像千问项目一样在 `answer` 阶段之前被正确捕获并返回给客户端。
- **多模态适配**: 智谱支持图片 URL/Base64，需适配 OpenAI 的 `image_url` 格式。
- **鉴权一致性**: 统一使用项目的 `VALID_TOKENS` 机制。

---

## 工作目标

### 核心目标
创建一个稳定、高性能的智谱AI反向代理服务，使本地工具（如 Cherry Studio, NextChat）可以通过标准 OpenAI 协议调用 GLM-4 模型。

### 验收标准
- [ ] `/v1/chat/completions` 接口成功响应非流式请求，返回 JSON 格式正确。
- [ ] `/v1/chat/completions` 接口成功响应流式请求，SSE 格式兼容 OpenAI。
- [ ] 开启思考模式时，返回内容包含 `reasoning_content` 字段。
- [ ] 视觉模型能够识别并分析传入的图片内容。

### 必须包含
- 完善的日志记录（不泄露 API Key）。
- 自动的模型 ID 映射（OpenAI 模型名 -> 智谱模型名）。
- 健康检查端点 `/health`。

### 禁止包含
- 硬编码的密钥。
- 侵入性地修改现有千问项目代码（保持功能独立）。

---

## 验证策略 (MANDATORY)

### 测试决策
- **基础设施存在**: 是 (FastAPI + uvicorn)
- **QA 方法**: 手动自动化验证 (Manual-only with automated procedures)

### 自动化验证程序

**对于聊天补全 (Chat Completions)**:
```bash
# 验证非流式
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4-flash", "messages": [{"role": "user", "content": "你好"}]}'

# 验证流式与思维链
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4.5-flash", "messages": [{"role": "user", "content": "1+1="}], "stream": true, "enable_thinking": true}'
```

---

## 执行策略

### 并行执行波次

```
Wave 1 (基础准备):
├── Task 1: 环境配置与依赖更新
└── Task 2: 客户端基础框架实现

Wave 2 (核心开发):
├── Task 3: 核心对话与 SSE 转换逻辑
└── Task 4: FastAPI 服务与鉴权中间件

Wave 3 (完善交付):
├── Task 5: 多模态适配与高级参数处理
└── Task 6: 文档编写与最终验证
```

### 依赖矩阵

| 任务 | 依赖项 | 阻塞项 | 可并行项 |
|------|------------|--------|---------------------|
| 1 | 无 | 无 | 2 |
| 2 | 无 | 3, 4 | 1 |
| 3 | 2 | 5 | 4 |
| 4 | 2 | 6 | 3 |
| 5 | 3 | 6 | 4 |
| 6 | 4, 5 | 无 | 无 |

---

## TODOs

### Wave 1: 基础准备

- [ ] 1. 环境配置与依赖更新

  **要做的事情**:
  - 更新 `.env.example`，添加 `ZHIPU_API_KEY` 相关字段。
  - 检查 `requirements.txt`，确保 `requests`, `fastapi`, `python-dotenv` 等版本满足智谱 API 开发需求。

  **推荐 Agent Profile**:
  - **Category**: `writing`
  - **Skills**: [`python-dotenv`]

  **并行化**: Wave 1
  **参考**: `.env.example`, `requirements.txt`

- [ ] 2. 客户端基础框架实现 (`bigmodel_client.py`)

  **要做的事情**:
  - 创建 `BigModelClient` 类。
  - 实现 `__init__` 方法，配置 `api_key` 和 `base_url`。
  - 实现 `_init_headers`，封装 Bearer Token 认证。
  - 定义 `MODEL_MAP` 映射表，包含 `glm-4-flash`, `glm-4-plus` 等主要模型。

  **推荐 Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: [`requests`]

  **并行化**: Wave 1
  **参考**: `qwen_reverse_fastapi.py:441-481` (QwenClient 初始化参考)

### Wave 2: 核心开发

- [ ] 3. 核心对话与 SSE 转换逻辑

  **要做的事情**:
  - 在 `BigModelClient` 中实现 `chat_completions` 方法。
  - 实现 `_streaming_response` 内部生成器。
  - 解析智谱 SSE 行（`data: `），提取 `choices[0].delta.content` 和 `reasoning_content`。
  - 构造标准的 OpenAI Chunk 格式（含 `id`, `object`, `created`, `model` 等字段）并返回。
  - 实现非流式聚合逻辑。

  **推荐 Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`requests`, `json`]

  **并行化**: Wave 2
  **依赖**: Task 2
  **参考**: `qwen_reverse_fastapi.py:927-1048` (流式响应解析逻辑)

- [ ] 4. FastAPI 服务与鉴权中间件 (`bigmodel_reverse_fastapi.py`)

  **要做的事情**:
  - 初始化 FastAPI 应用。
  - 迁移或复用 `verify_auth_token` 逻辑，支持从环境变量 `VALID_TOKENS` 读取授权。
  - 实现 `/v1/chat/completions` POST 路由，分发给 `BigModelClient`。
  - 实现 `/v1/models` (GET) 和 `/health` (GET) 路由。

  **推荐 Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`fastapi`]

  **并行化**: Wave 2
  **依赖**: Task 2
  **参考**: `qwen_reverse_fastapi.py:1-224` (FastAPI 架构与鉴权)

### Wave 3: 完善交付

- [ ] 5. 多模态适配与高级参数处理

  **要做的事情**:
  - 在 `BigModelClient` 中增加对 `messages` 中多模态 `content` 数组的解析。
  - 将 OpenAI 的 `image_url` 映射为智谱 API (v4) 所需的 `image_url` 结构。
  - 处理 `enable_thinking` 参数，将其透传为智谱 API 的 `thinking` 配置。
  - 完善错误处理机制，捕获 HTTP 错误并映射为标准 OpenAI Error JSON。

  **推荐 Agent Profile**:
  - **Category**: `ultrabrain`

  **并行化**: Wave 3
  **依赖**: Task 3

- [ ] 6. 文档编写与最终验证

  **要做的事情**:
  - 编写 `README_BIGMODEL.md`，包含获取 API Key 的步骤、环境变量配置、模型列表及详细的 `curl` 示例。
  - 执行最终的端到端验证，确保在流式模式下思维链和最终回答能正确下发。

  **推荐 Agent Profile**:
  - **Category**: `writing`

  **并行化**: Wave 3
  **依赖**: Task 4, Task 5

---

## 提交策略

| 任务阶段 | 提交消息 (中文) | 文件 |
|------------|---------|-------|
| Wave 1 | `feat(bigmodel): 初始化客户端框架与环境配置` | `bigmodel_client.py`, `.env.example`, `requirements.txt` |
| Wave 2 | `feat(bigmodel): 实现聊天补全接口及流式SSE转换` | `bigmodel_client.py`, `bigmodel_reverse_fastapi.py` |
| Wave 3 | `feat(bigmodel): 完善多模态支持与项目文档` | `bigmodel_client.py`, `README_BIGMODEL.md` |

---

## 成功标准 (Definition of Done)

### 验证命令
```bash
# 模型列表验证
curl http://localhost:8000/v1/models

# 聊天补全验证 (流式)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

### 最终清单
- [ ] `bigmodel_client.py` 完整实现 API 封装。
- [ ] `bigmodel_reverse_fastapi.py` 成功运行并兼容 OpenAI。
- [ ] 流式思维链 (`reasoning_content`) 字段透传正常。
- [ ] 多模态图片理解功能正常。
- [ ] 文档详尽且包含所有必要配置说明。
