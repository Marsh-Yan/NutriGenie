# NutriGenie

> 基于 RAG 混合推荐的个性化营养规划系统。

NutriGenie 是一个面向个人作品集的端到端 AI 应用 Demo。用户可以完善饮食画像，并用自然语言描述健康目标、预算、过敏原、忌口和家中库存；系统通过结构化约束、混合检索和可解释的排序流程，生成菜谱推荐、3/7 天饮食计划、营养报告和采购清单。

项目的核心设计是 **Calculation First**：TDEE、营养、预算、过敏原和硬性饮食约束由确定性代码负责，LLM 主要用于自然语言意图理解和结果总结，RAG 用于增强“暖胃”“快手”“不想吃水煮菜”等模糊场景的语义召回。

> 当前项目定位为学习与作品集 Demo，不建议直接用于生产环境，也不构成医疗或营养治疗建议。

## 界面展示

### 首页

![NutriGenie 首页](screenshots/home.png)

### 饮食计划结果页

![NutriGenie 饮食计划结果页](screenshots/plan-result.png)

## 功能概览

- 用户注册、登录和个人饮食画像管理
- 根据目标、饮食类型、预算、过敏原和库存生成个性化计划
- 支持自然语言输入，并在 LLM 不可用时回退到规则解析
- MySQL 结构化候选与 Chroma 向量检索融合
- 过敏原、忌口、饮食类型等硬约束过滤
- 按营养、预算、偏好、语义相关性和库存利用率进行确定性重排
- 异步生成计划，前端轮询展示处理进度
- 生成每日计划、营养报告、采购清单和推荐解释
- 管理员维护食材、菜谱和 RAG 知识文档
- 提供 RAG 检索评测与推荐效果对照脚本

## 系统架构

```text
Vue 3 + TypeScript
        │  REST API / 状态轮询
        ▼
FastAPI + LangGraph 工作流
        │
        ├─ 意图解析（DeepSeek / 规则回退）
        ├─ 约束分析（TDEE、预算、饮食类型、过敏原）
        ├─ 混合召回（MySQL + Chroma）
        ├─ 硬约束过滤与确定性重排
        ├─ 计划聚合与结果校验
        └─ 基于证据的结果总结
        │                         │
        ▼                         ▼
MySQL：业务主数据          Chroma：可重建语义索引
```

### 推荐链路

```text
用户自然语言需求
  → 意图与约束解析
  → 结构化候选查询 + 语义召回
  → 过敏原/忌口/饮食类型硬过滤
  → 营养、预算、偏好、语义和库存利用率混合重排
  → 3/7 天计划、营养报告和采购清单
  → 基于推荐证据的总结
```

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Element Plus、Pinia、ECharts |
| 后端 | FastAPI、SQLAlchemy、Alembic、Pydantic |
| 工作流 | LangGraph、确定性约束与排序服务 |
| 数据库 | MySQL；测试使用 SQLite 内存数据库 |
| RAG | Chroma、Markdown 知识文档、智谱 Embedding |
| LLM | DeepSeek，用于意图解析和结果总结 |
| 任务执行 | 本地后台线程；知识库索引可选 RQ/Redis |

## 项目结构

```text
NutriGenie/
├─ backend/
│  ├─ app/
│  │  ├─ api/              # REST API 路由与请求模型
│  │  ├─ db/               # 数据库连接与种子数据
│  │  ├─ models/           # SQLAlchemy 数据模型
│  │  ├─ rag/              # 文档解析、Embedding、Chroma 检索与评测
│  │  ├─ services/         # 营养、成本、约束、推荐和安全服务
│  │  └─ workflow/         # LangGraph 工作流与提示词
│  ├─ knowledge_base/      # 菜谱 RAG 增强文档
│  ├─ scripts/             # 初始化、建索引、评测和管理员脚本
│  ├─ tests/               # 单元测试与集成测试
│  ├─ .env.example         # 环境变量模板
│  └─ requirements.txt
├─ frontend/
│  ├─ src/api/             # Axios API 封装
│  ├─ src/components/      # 通用、计划和菜谱组件
│  ├─ src/stores/          # Pinia 状态
│  ├─ src/views/           # 首页、画像、计划和管理页面
│  └─ package.json
├─ docs/                   # 产品、架构、API、RAG 和开发文档
├─ .gitignore
└─ README.md
```

## 本地运行

### 环境要求

- Python 3.11 或更高版本
- Node.js 20 或更高版本
- MySQL 8.0 或更高版本（正式或完整数据环境；快速演示可使用 SQLite）
- 可选：Redis，用于将知识库索引任务切换到 RQ 队列
- 可选：DeepSeek API Key 和智谱 Embedding API Key

### 1. 创建数据库

如果只是本地演示，可以先使用免安装的 SQLite。在 `backend/.env` 中设置：

```dotenv
DATABASE_URL_OVERRIDE=sqlite:///./data/nutrigenie.db
```

然后直接继续第 2 步，种子脚本会自动创建数据库文件。需要正式或多人环境时，再创建 MySQL 数据库：

先创建一个空的 MySQL 数据库，名称需要与 `backend/.env` 中的 `DB_NAME` 保持一致。示例：

```sql
CREATE DATABASE nutrigenie
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2. 配置并启动后端

以下命令以 PowerShell 为例：

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少确认以下配置：

| 变量 | 说明 |
| --- | --- |
| `DB_HOST` / `DB_PORT` | MySQL 地址和端口 |
| `DB_USER` / `DB_PASSWORD` | MySQL 登录信息 |
| `DB_NAME` | 数据库名称，默认 `nutrigenie` |
| `DATABASE_URL_OVERRIDE` | 可选；快速演示可设为 `sqlite:///./data/nutrigenie.db` |
| `LLM_API_KEY` | DeepSeek Key；为空时使用规则/模板回退路径 |
| `EMBEDDING_API_KEY` | 智谱 Embedding Key；启用 RAG 建索引时需要 |
| `JWT_SECRET_KEY` | JWT 签名密钥，部署时必须替换为随机高强度字符串 |
| `DEV_EMAIL_VERIFICATION_CODE` | 本地注册验证码，仅供开发演示 |
| `KNOWLEDGE_QUEUE_BACKEND` | 默认 `background`；使用 RQ 时设置为 `rq` |

初始化数据库和种子数据：

```powershell
python -m app.db.seed
```

生成菜谱知识文档并构建 Chroma 索引（已配置 `EMBEDDING_API_KEY` 时执行）：

```powershell
python scripts\generate_recipe_knowledge.py
python scripts\build_rag_index.py
```

启动 API 服务：

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

后端接口文档：<http://localhost:8000/docs>

### 3. 启动前端

另开一个终端：

```powershell
cd frontend
npm ci
npm run dev
```

前端默认地址：<http://localhost:5173>

Vite 开发服务器会将 `/api` 请求代理到 `http://localhost:8000`。前端页面包含公开 Demo（`/demo`）、登录注册、画像、计划和管理员页面。

### 4. 创建管理员账号（可选）

在 `backend/.env` 中配置 `ADMIN_EMAIL`、`ADMIN_PASSWORD` 和可选的 `ADMIN_NICKNAME`，然后运行：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.create_admin
```

管理员可以访问食材、菜谱和知识库管理页面。

## 测试与评测

运行不依赖真实 MySQL 的默认测试：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

运行需要 MySQL 和种子数据的集成测试：

```powershell
python -m pytest tests -m integration -q
```

运行推荐效果对照评测：

```powershell
python scripts\evaluate_recommendation.py
```

评测输入位于 `backend/evaluation/cases.json`，报告默认生成到 `backend/evaluation/reports/`。一次本地评测快照（2026-08-01，30 条用例）如下：

| 指标 | 规则 Baseline | Hybrid RAG |
| --- | ---: | ---: |
| HitRate@5 | 83.33% | 83.33% |
| Precision@5 | 29.33% | 35.33% |
| 硬约束违规数 | 0 | 0 |

该结果用于展示当前 Demo 的评测方法，不代表所有数据集或生产场景的效果。建议使用评测脚本重新生成报告。

## 安全与开源发布检查

- 不要提交 `backend/.env`、任何 API Key、数据库密码、JWT 密钥或管理员密码。
- 只提交 `backend/.env.example`，并在真实环境中填写密钥。
- 生产环境必须关闭调试模式、替换 JWT 密钥、配置真实邮箱验证流程，并限制 CORS 来源。
- 不要将 API Key 放入前端代码或打包产物。
- `backend/data/chroma/`、`backend/evaluation/reports/`、Python 虚拟环境、`node_modules/` 和前端 `dist/` 都属于本地或生成文件，不应提交。
- 如果密钥曾经被提交、上传、截图或分享过，应先在对应平台撤销并重新生成，再公开仓库。

当前仓库中的食品、营养和菜谱内容主要用于作品集演示。正式使用前应替换为来源可验证、具备授权或合规依据的数据。

## 文档说明

项目中的个人笔记、面试材料和开发过程文档不纳入公开仓库。公开版本以本 README、代码结构和接口文档为准。

## 项目限制

- 本项目是一般健康饮食参考工具，不提供疾病诊断、治疗或个体化医疗建议。
- 周计划采用启发式规划和结果校验，不保证全局最优，也不能替代专业营养师建议。
- 当前邮件验证码为本地开发演示机制，不适用于生产环境。
- RAG 索引依赖外部 Embedding 服务；未配置时可使用规则推荐和回退总结路径，但语义检索能力不可用。
- 当前任务执行以单进程本地后台线程为主，生产部署应替换为可靠的任务队列和持久化监控方案。

## 许可证

本项目目前尚未附带许可证。公开仓库前，请根据你的授权意愿补充 `LICENSE` 文件；未声明许可证不等于默认允许他人自由复制、修改或分发。
