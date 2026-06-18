# helper-agent

基于 FastAPI + Vue 3 的 AI 对话系统，支持 DeepSeek 和 Qwen 模型。

## 项目结构

```
agent-demo/
├── backend/                 # 后端服务
│   ├── api/                 # API路由
│   │   ├── chat.py         # 聊天接口
│   │   ├── sessions.py     # 会话管理
│   │   └── upload.py       # 文件上传
│   ├── services/           # 业务服务
│   │   ├── deepseek_service.py
│   │   └── qwen_service.py
│   ├── main.py             # FastAPI入口
│   ├── config.py           # 配置管理
│   └── requirements.txt    # Python依赖
│
└── frontend/               # 前端应用
    ├── src/
    │   ├── components/      # Vue组件
    │   │   ├── Sidebar.vue
    │   │   ├── ChatArea.vue
    │   │   ├── MessageBubble.vue
    │   │   ├── InputArea.vue
    │   │   ├── Settings.vue
    │   │   ├── ModelSelector.vue
    │   │   └── UploadButton.vue
    │   ├── api/            # API调用
    │   │   └── index.js
    │   ├── stores/         # Pinia状态管理
    │   │   └── chat.js
    │   ├── App.vue
    │   └── main.js
    └── package.json
```

## 快速开始

### 1. 克隆并安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
QWEN_API_KEY=your_qwen_api_key_here

# 可选：阿里云OSS配置（用于文件上传）
ALIYUN_OSS_ACCESS_KEY_ID=your_oss_access_key_id
ALIYUN_OSS_ACCESS_KEY_SECRET=your_oss_access_key_secret
ALIYUN_OSS_BUCKET_NAME=your_bucket_name
ALIYUN_OSS_ENDPOINT=your_endpoint
```

### 3. 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 http://localhost:8000 启动

### 4. 安装前端依赖并启动

```bash
cd frontend
npm install
npm run dev
```

前端应用将在 http://localhost:3000 启动

## 功能特性

- ✅ 多模型支持（DeepSeek / Qwen）
- ✅ 模型切换器
- ✅ 流式响应（SSE）
- ✅ 会话管理（创建、切换、删除）
- ✅ Markdown渲染与代码高亮
- ✅ 模型参数设置（温度、最大Token数）
- ✅ 本地存储持久化
- ✅ 文件上传（支持本地存储和阿里云OSS）
- ✅ 暗色主题切换
- ✅ 对话搜索（支持标题和内容搜索）

## API文档

启动后端服务后，访问 http://localhost:8000/docs 查看完整的 API 文档。

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/chat` | POST | 发送聊天消息 |
| `/api/models` | GET | 获取支持的模型列表 |
| `/api/sessions` | GET | 获取会话列表 |
| `/api/sessions` | POST | 创建会话 |
| `/api/sessions/{id}` | GET | 获取会话详情 |
| `/api/sessions/{id}` | DELETE | 删除会话 |
| `/api/sessions/{id}/messages` | POST | 添加消息到会话 |
| `/api/upload` | POST | 上传文件 |
| `/uploads/{filename}` | GET | 获取上传的文件 |

## 技术栈

- **后端**: FastAPI, Python 3.8+
- **前端**: Vue 3, Vite, Element Plus, Pinia
- **AI模型**: DeepSeek API, Qwen API
- **存储**: 阿里云OSS（可选，支持本地存储备选）
