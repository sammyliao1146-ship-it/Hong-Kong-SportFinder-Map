# 动向香港 · HK SportFinder

香港运动场所可视化地图，结合公开设施数据、可获得的预约余量与 AI 选场助手。

本仓库处于架构与骨架阶段：全屏底图、主动定位、固定顶栏、左侧设施索引菜单与顶栏下方的展开式搜索、
右下角 AI 聊天气泡、FastAPI 接口、数据源目录和 Agent 对话已搭建；已接入六类 CSDI 设施图层，支持地图标记、设施类型筛选、名称/地址搜索和场所详情；预约文件适配尚未实现。
页面上的记录数是用户提供的 2026-10-22 研究快照，不是本程序新查询的数量。

## 目录

```text
frontend/                 React + TypeScript + Vite + Leaflet / MapLibre
  src/api/                后端 API 客户端
  src/features/map/       地图、主动定位
  src/features/search/    独立的设施索引菜单与展开式搜索面板
  src/features/assistant/ AI 气泡与展开式聊天窗口
backend/                  FastAPI 服务
  app/api/routes/         HTTP 接口
  app/core/               服务配置
  app/domain/             统一场所与余量模型
  app/data/               数据源目录
  app/services/           地图与 Agent 共用的数据服务
  tests/                  接口及数据语义测试
agent/                    OpenAI Agents SDK（由后端进程调用）
  tools/                  由后端注入的数据查询工具
  prompts.py              选场规则
  service.py              模型连接与 Agent 运行

docs/ARCHITECTURE.md      架构、数据模型、接口与开发顺序
docs/PROJECT_CONTEXT.md   已有研究及未验证事项
```

## 本地启动

Python 3.12+；Node.js 22.12+（或满足 Vite 7 要求的 Node 20.19+）。

在项目根目录执行：

```bash
cd '/Users/liaoshiyu/hk sports'
python3 -m venv .venv  # 已有 .venv 时跳过
.venv/bin/python -m pip install -e '.[dev]'
cp -n .env.example .env  # 已有配置时保留
```

编辑根目录 `.env` 中的 `BAI_API_KEY`、`BAI_MODEL`、`BAI_BASE_URL`。
后端读取根目录 `.env`；现有进程环境变量优先。密钥只在服务器使用。

第一个终端：

```bash
cd '/Users/liaoshiyu/hk sports'
.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

第二个终端：

```bash
cd '/Users/liaoshiyu/hk sports/frontend'
npm install
npm run dev
```

- 前端：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/v1/health

前端开发服务器把 `/api` 代理到 FastAPI。后续部署采用同域反向代理。
开发底图使用 OpenFreeMap 的 Positron 浅色矢量样式，通过 MapLibre 在 Leaflet 中按需加载；
保留 OpenFreeMap、OpenMapTiles 和 OpenStreetMap 归属信息，不预下载香港底图。
正式部署前确认瓦片服务提供商及其使用条件。

## 当前接口

| 方法 | 路径 | 当前行为 |
| --- | --- | --- |
| GET | `/api/v1/health` | 服务健康检查 |
| GET | `/api/v1/sources` | 六个来源及真实接入状态 |
| GET | `/api/v1/venues` | 同步六类官方图层；返回名称、地址、WGS84 坐标及状态，支持部分失败与旧缓存回退 |
| POST | `/api/v1/assistant/chat` | `{"message":"hi"}`；由 Agents SDK 调用 B.AI Responses 接口 |

Agent 当前支持 `inspect_data_status` 工具，尚无实际场所或余量查询工具。
每次提问独立处理，无对话历史。未配置密钥时数据与地图接口仍可运行，AI 接口返回 503。

## 验证

```bash
cd '/Users/liaoshiyu/hk sports'
.venv/bin/python -m pytest
cd frontend
npm run build
```

本地测试不调用付费模型。真实模型请求仅在用户通过 AI 面板或 API 主动提交时发起。

## 资料

- [架构规划](docs/ARCHITECTURE.md)
- [项目研究上下文](docs/PROJECT_CONTEXT.md)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
- [B.AI API](https://docs.b.ai/llmservice/api/)

当前搜索支持设施类型、场所中英文名称、地址和地区；点击场所结果定位地图。设施索引与搜索面板互斥展开，小屏幕下它们与聊天窗口也互斥展开；关闭聊天保留本次草稿和结果。

界面结构：顶栏最左侧为设施索引入口；搜索条位于顶栏下方，点击展开输入框和匹配列表。选择分类后菜单收起，顶栏显示可清除的筛选标签。

## 设施数据同步

首次请求 `/api/v1/venues` 时并行查询六个 CSDI 图层，按 OBJECTID 分页。
后端每小时按需更新，进程内共享缓存并保存到 `data/cache/venues.json`，无需数据库即可运行。
上游失败保留该图层旧数据；没有旧数据时返回明确错误状态，不把失败当作零场地。失败后至少间隔 60 秒重试。
Render 默认文件系统非持久化，重部署后可重新从官方接口拉取；多实例部署时应迁移到共享数据库或缓存。
返回 total 为图层记录数，并非去重场所总数。坐标不保证是入口；未接入预约数据，所有场地余量未知。

## 索引与预约余量

设施索引支持多选及默认收起的子设施；按已发布的运动字段匹配，不从“硬地球场”推断具体运动。
第二个索引标签切换为预约空位地图，通过 `/api/v1/availability?sport=badminton` 获取五类官方 SmartPLAY 数据：
`badminton`、`basketball`、`volleyball`、`tennis`、`turf-soccer-pitch`。
每种运动后端缓存 5 分钟并持久化到 `data/cache/bookings/`；失败回退到旧快照并标记 stale。
页面在预约模式下每 5 分钟重新读取，切换运动取消旧请求。刷新按钮读取服务端当前快照，不绕开缓存。
按所选日期汇总上午（12 点前）、下午（12–18 点）、晚上（18 点起）的可订场次之和；这不是球场总数。
明细表按官方起止时间逐格显示剩余场数，点击格子查看各场区拆分。0、未知、旧快照分别显示；缺少坐标的场馆只出现在列表中。
导航使用 Google Maps Directions URL；体育馆简介链接定位康文署对应地区页面内的场馆标题，其他场地优先采用官方提供的网页，缺失时链接至政府场所目录。

公开余量项目已按政府全量目录核查，当前确认的五类均已接入。前端运动清单由
`GET /api/v1/availability/sports` 提供，与后端来源登记保持一致。
核查方法和范围见 [公开余量覆盖说明](docs/BOOKING_DATA_COVERAGE.md)。
