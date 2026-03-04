# 智谱AI (BigModel) 反向代理实现计划草稿

## 需求确认摘要

### 核心开发范围
1. **bigmodel_client.py** - Cookie管理器和BigModelClient类
2. **bigmodel_reverse_fastapi.py** - FastAPI主程序
3. **更新 .env.example** - 环境变量模板

### 功能范围（已确认）
**包含**：
- 流式/非流式响应支持
- 基础OpenAI API兼容
- Cookie认证机制
- 配置驱动，使用者自行提供Cookies和API端点

**不包含**（后续扩展）：
- 多模态对话（图片上传）
- 文件上传功能
- 会话历史管理
- 复杂的Cookie健康检查机制
- OpenAI高级参数（functions, tools等）

### 错误处理策略
- Cookie未配置提示
- API请求失败处理
- 基本错误响应格式
- 不包括复杂的Cookie健康检查

### OpenAI兼容性范围
**支持参数**：
- `model` - 模型名称
- `messages` - 消息数组
- `stream` - 是否流式响应
- `temperature` - 温度参数（可选）
- `max_tokens` - 最大Token数（可选）

**不支持**：
- `functions` / `tools` 调用
- `response_format` 限制
- `logprobs` 参数
- 高级推理参数

### 测试策略
- 暂时不包含完整单元测试
- 先实现核心功能
- 后续可添加基本集成测试

### 核心设计原则
- 简单、配置驱动
- 使用者可自行调整API端点和参数映射
- 参考千问项目的架构，但不做过度设计

---

## 依赖分析

### 外部依赖（Python包）
- `fastapi >= 0.116.1` - Web框架
- `uvicorn >= 0.35.0` - ASGI服务器
- `requests >= 2.32.4` - HTTP客户端
- `python-dotenv >= 1.1.1` - 配置管理
- `pydantic >= 2.8.2` - 数据验证
- `python-multipart >= 0.0.6` - 文件上传支持

### 内部依赖关系
```
.env.example → bigmodel_client.py → bigmodel_reverse_fastapi.py
              ↑
              配置模板提供环境变量名称和默认值
```

### 执行顺序
1. **第一阶段**：更新 .env.example（无依赖，独立任务）
2. **第二阶段**：实现 bigmodel_client.py（无外部依赖，独立任务）
3. **第三阶段**：实现 bigmodel_reverse_fastapi.py（依赖 bigmodel_client.py）

---

## 并行执行分析

### 可并行任务
- **无**：所有任务存在依赖关系，必须串行执行
  - .env.example 更新必须在开发初期完成（为后续代码提供配置规范）
  - bigmodel_client.py 必须在 bigmodel_reverse_fastapi.py 之前完成（主程序依赖客户端类）

### 任务依赖图
```
任务1: 更新 .env.example
   ↓
任务2: 实现 bigmodel_client.py
   ↓
任务3: 实现 bigmodel_reverse_fastapi.py
```

### 预计总工时
- 简单任务（预计1-2小时实际开发时间）
- 主要时间用于确保代码质量和与千问项目的架构一致性

---

## 关键设计决策

### 1. CookieManager 类设计
- 简化版本，不包含复杂的健康检查
- 基础解析和验证功能
- 参考千问项目的 CookieManager 实现模式

### 2. BigModelClient 类设计
- 支持自定义 API 端点配置
- 流式/非流式响应处理
- OpenAI 格式转换逻辑
- 使用 requests 库保持与千问项目一致

### 3. FastAPI 应用设计
- 基础 API 端点（/, /health, /v1/models, /v1/chat/completions）
- Bearer Token 认证
- 简化的 CORS 配置
- 日志配置（参考千问项目模式）

### 4. 配置文件设计
- 环境变量驱动的配置方式
- 提供 .env.example 模板
- 支持 JSON 和逗号分隔格式的 Token 列表

---

## 待确认问题

### 已确认 ✓
- 测试策略：暂不包含单元测试
- 功能范围：仅基础聊天补全
- 错误处理：基础级别
- OpenAI 兼容性：基本兼容

### 无待确认问题
所有需求细节已明确，可以开始制定完整执行计划。
