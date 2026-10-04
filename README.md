# 用健康知识助手学习 FastAPI

这是面向 Python 初学者的本地教学项目。没有配置 Key 时运行关键词规则版；配置 `DEEPSEEK_API_KEY` 后，同一个 FastAPI 接口会改用 DeepSeek API。不保存聊天内容。它不是医疗产品。页面不保存会话，但浏览器、开发工具以及模型服务仍可能处理或留有请求内容，请勿输入真实病历或个人身份信息。

## 先理解这三个角色

- **FastAPI**：Python Web 框架，接收 HTTP 请求、校验数据、调用函数、返回 JSON，并生成 API 文档。
- **Agent**：负责决定下一步做什么、使用什么工具。本项目先检索本地知识库，再将相关片段交给模型。
- **大模型**：可用于理解问题和组织语言，但不是 FastAPI 的组成部分。配置本地 `.env` 后，项目会调用 DeepSeek。
- **模型适配层**：`app/llm.py` 负责 DeepSeek SDK、模型名称、超时和错误转换。

本项目的数据流：浏览器 → POST /api/chat → ChatRequest 校验 → run_agent → 本地知识检索 → 命中后调用 DeepSeek → 返回答案和来源。没有命中时不会把问题发给 DeepSeek。

## 本地知识库（RAG）

知识文件放在 `knowledge_base/`，支持 UTF-8 的 Markdown 和 TXT。项目附带一份一般健康知识示例。页面下方可以上传你自己的 `.md` 或 `.txt` 文件，也可以把文件放到该目录，再重启服务。上传的文件名会安全改写，上传文档默认被 Git 忽略；不要放个人病历或身份信息。

Markdown/TXT 可用空行分段。想显示可点击的公开来源时，在对应资料段前写一行来源：

```markdown
# 高血压健康教育

来源: https://example.org/verified-guide

这里是经核实、适用于一般健康教育的资料段落。
```

当前检索使用本地中文二字片段和英文词的轻量级词面匹配，不是语义向量搜索。它只读取 `knowledge_base/` 里的文件，不会联网查资料。模型只收到命中的文本片段，并被要求依据这些片段回答；没有命中时，接口不调用模型。返回的来源指向片段中的公开来源，或指向本地文档查看接口。

回答风格也在 `app/llm.py` 的系统提示中约束为简短纯文本（默认不超过两句话），并在返回前清理常见 Markdown 标记。这能减少多余格式，但模型输出仍可能不完全遵守约束。

可以查看 `GET /api/knowledge` 的已收录文档列表。上传接口为 `POST /api/knowledge`，由页面以 multipart 文件表单调用。

## 配置 DeepSeek Key

把项目根目录的 `.env.example` 复制一份并命名为 `.env`，用文本编辑器打开 `.env`，只在本机填入你的 Key：

```powershell
Copy-Item .env.example .env
```

把 `.env` 内容改为 `DEEPSEEK_API_KEY=你的密钥`，保存后运行项目根目录的 `启动医疗助手.bat`。程序启动时会自动读取 `.env`；Key 不会提交到 Git。访问 `/health`，看到 `mode` 为 `deepseek_rag` 表示已启用。项目使用 DeepSeek 官方兼容格式：OpenAI Python SDK + `https://api.deepseek.com`。

## 启动（Windows PowerShell）

进入本 README 所在目录执行。已创建环境的情况下可以跳过第一行；不需要激活环境，也无需修改 PowerShell 执行策略。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

也可以双击 `启动医疗助手.bat` 启动。

打开 http://127.0.0.1:8000 体验页面，打开 http://127.0.0.1:8000/docs 使用交互式 API 文档。终端按 Ctrl+C 停止。若端口被占用，将 8000 换成 8001。`--reload` 方便学习时自动加载修改，仅用于开发。

## 你的第一节课（约 30 分钟）

1. 打开 `/docs`，展开 `GET /health`，点击 Try it out → Execute，观察返回的 JSON。
2. 展开 `POST /api/chat`，提交 `{"message":"如何保持健康饮食？"}`。观察 `answer`、`route`、`sources`、`steps`。
3. 把 message 改成空字符串，观察 HTTP 422：这是输入校验失败，业务函数不会执行。
4. 打开 `app/main.py`，找到 `@app.post`。它把 URL 和 Python 函数连起来；payload 是解析后的请求体。
5. 打开 `app/agent.py`，给饮食主题增加关键词“膳食”，保存后再提问“膳食建议”，验证自己第一次修改。

## 七次练习路线（每次 30–60 分钟）

| 次数 | 学什么 | 动手做什么 | 完成标准 |
| --- | --- | --- | --- |
| 1 | Python 函数、字典、类型提示；HTTP 请求/响应 | 按上一节运行项目并读 `/health` | 能说清浏览器如何调用 Python 函数 |
| 2 | GET、POST、路由、JSON | 增加 `GET /about` 返回项目介绍 | 在 `/docs` 中看到并调用它 |
| 3 | Pydantic 与 422 | 给 ChatRequest 增加可选 language 字段，限制为 zh/en | 非法语言返回 422；注意当前知识仍是中文 |
| 4 | 查询参数、路径参数、404 | 调用 `/api/topics?q=饮食` 与 `/api/topics/diet`，再传不存在的 id | 能区分查询参数、路径参数、请求体 |
| 5 | 工作流与工具 | 阅读 run_agent；补充一个经核实、附来源的健康知识主题 | 新主题能命中，未知问题仍明确表示不知道 |
| 6 | 自动测试与模块拆分 | 运行测试；为新主题增加一条测试 | 修改前后测试均通过，知道测试在保护什么 |
| 7 | 升级设计 | 画出“边界检查 → 检索 → 模型生成 → 返回来源”的流程，设计 provider 接口 | 能解释哪些代码需要替换、哪些接口保持稳定 |

若函数、列表和字典还不熟悉，先花 1–2 次练习写一个命令行关键词问答，再进入第 1 次练习。无需先学 Docker、数据库或大型 Agent 框架。

## 文件怎么读

按 `main.py → schemas.py → agent.py → tests/test_api.py` 的顺序阅读。

- `app/main.py`：路由、路径/查询参数、HTTP 错误、页面入口。
- `app/schemas.py`：请求与响应契约，字符串长度与类型校验。
- `app/agent.py`：紧急相关词规则、检索优先的工作流以及模型调用编排。
- `app/knowledge.py`：文档读写、分段和本地检索。
- `app/llm.py`：只根据检索片段调用 DeepSeek。
- `knowledge_base/`：初始和用户添加的 Markdown/TXT 知识文件。
- `app/static/index.html`：用 fetch 调用 API，展示真实请求与响应。
- `tests/test_api.py`：接口测试，覆盖校验、来源、边界分支和 404。

## 当前接口

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| GET | /health | 检查服务状态 |
| GET | /api/topics?q=饮食 | 查询参数示例 |
| GET | /api/knowledge | 查看本地知识文档 |
| POST | /api/knowledge | 上传 Markdown/TXT 文档 |
| GET | /api/knowledge/{doc_id} | 查看知识文档 |
| POST | /api/chat | 先检索知识，再按配置调用模型 |
| GET | / | 教学页面 |

PowerShell 也能直接调用：

```powershell
$payload = @{message = '如何保持健康饮食？'} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/chat' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
```

测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 下一版再做什么

1. **模型接入**：选定服务后新增 provider 模块；密钥仅放服务端环境变量，设置超时、错误处理；用假 provider 测试，避免每次测试付费。异步网络请求时再学习 `async def` 与 `await`，不是给所有函数加 async 就会更快。
2. **检索增强（RAG）升级**：目前已经实现本地词面检索；下一步可学习向量检索、文档版本和检索质量评估，保持只根据实际命中的资料回答。
3. **多轮对话**：先用虚构数据学习 session_id，再考虑数据库、会话隔离、删除与保存期限。
4. **真实应用前**：医疗专家评估、隐私保护、身份验证、监控和系统性安全评测，需要单独设计。

当前关键词规则会漏报、误报，也不理解否定和上下文；紧急词提示不能作为分诊依据。它只用于观察分支优先级。没有触发提示不代表安全，来源也不代表 WHO 对本项目背书。

## 官方参考资料

- [FastAPI 第一步](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [请求体与 Pydantic](https://fastapi.tiangolo.com/tutorial/body/)
- [接口测试](https://fastapi.tiangolo.com/tutorial/testing/)
- [WHO 健康饮食](https://www.who.int/news-room/fact-sheets/healthy-diet)
- [WHO 身体活动](https://www.who.int/news-room/fact-sheets/detail/physical-activity)

知识库仅含一般性摘要，来源核对日期：2026-09-29；不是实时检索。
