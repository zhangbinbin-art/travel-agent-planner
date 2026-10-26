# 版本发布说明 v0.9 —— 预算扩展（食宿/交通）+ 高德距离矩阵与 MySQL 落地

**Tag**：`v0.9-budget-amap` 　**基线**：`v0.8-favorite-budget` 　**HEAD**：`4b840df`
**代码量**：15 files changed, **+648 / −44**（后端 3370 行 / 前端 3603 行）

## 一、本次提交序列（4 个）

| 提交 | 类型 | 内容 |
|---|---|---|
| `288bf2a` | feat | 预算扩展食宿交通与高德距离矩阵降级（12 文件 +502/−27） |
| `a4a8501` | chore | 修复 test_v05 崩溃（审核流适配）、补 `requirements.txt`（33 包） |
| `4406925` | fix | MySQL 坐标 `Float(53)` 双精度修复 + `init_favorites.py` 幂等化 + `--yes` 保护 |
| `4b840df` | fix | 补注册 ECharts `GridComponent`，消除规划页 xAxis 控制台报错 |

## 二、已完成能力清单

### 1) 预算模型（v0.9 核心）
- 五项预算：**门票合计 / 食宿 / 交通 / 总预算 / 日均**，字段名 `ticket_total, hotel_total, traffic_total, grand_total, daily_avg`
- `hotel_per_day` 全链路透传（前端 → `schemas/trip.py` → `api/v1/trip.py` → `trip_service`），默认 `300 元/天`
- 交通单价固定 `1.5 元/km`（`core/pricing.py`，UI 只读不可改）
- 门票按景点名查表 `TICKET_PRICES`（西湖 0 / 故宫 60 / 外滩 0），未收录回退 50
- **向后兼容**：v0.8 存量 `route_json` 缺字段时整体重算，不 500；保留 legacy `daily_average`（门票日均）

### 2) 高德距离矩阵 + 降级
- `AMAP_KEY` 唯一入口 `core/config.py`；`_fetch_amap_distance` 用标准库 urllib 调驾车距离矩阵（经度在前）
- **三级兜底**：无 key / 请求异常 / 非 1 状态 / 空结果 → `_mock_distance`（hypot，1 坐标单位≈1km，与 v0.7/v0.8 结果一致 344.84 km）
- 兜底结果**同样入缓存**，避免反复重试烧额度；缓存键 `tuple(sorted(ids))`，提供 `clear_distance_cache()`
- 坐标脚本 `backend/scripts/init_spot_coords.py`（西湖 30.2417/120.15、故宫 39.9163/116.3972、外滩 31.2397/121.4909）
- Dijkstra / `build_graph` / `shortest_path` 零改动，路线结果与 v0.6 一致

### 3) 前端展示
- 规划页：单日食宿输入、五项预算卡、生成时**天数+单价快照**（`generatedHotelPerDay`，改输入不影响已生成预览/保存值）
- 我的路线卡片 / 详情弹窗：五项预算 + 路段距离 + 路线顺序评分
- 保存改用 `budget.days` 与生成时单价快照，预览与落库一致

### 4) 数据库工程化
- 支持 MySQL 8.0：`travel_bishe`，utf8mb4_0900_ai_ci，8 表全量迁移、主键保留、`auto_increment` 校正，**8/8 表按列比对 0 差异**
- 修复真实缺陷：SQLAlchemy `Float` → MySQL 4 字节单精度导致坐标截断（116.3972→116.397），改 `Float(53)` → DOUBLE
- `init_favorites.py` 去 DROP：幂等建表 + 唯一约束探测（SQLite `CREATE UNIQUE INDEX IF NOT EXISTS` / 其他方言 `ADD CONSTRAINT`）+ DELETE + 三重守卫；新增 `--yes`，缺省打印警告并 `exit 2`，**不建表不删数据**
- `requirements.txt`（33 包）；备份 `backend/travel_backup_v09_20261026.db`（90112B，integrity ok）

### 5) 测试与验收
- 回归：`test_v05` 正常清理 / `test_v06` **42 PASS** / `test_v07` **103 PASS** / `test_v08` **104 PASS**（SQLite 与 MySQL 双库各跑一遍）
- 浏览器端到端（Edge headless 真实 UI）：**29/29 PASS**，console 错误 **0**，4xx/5xx **0**
- 写入验证：新增行程确证落 MySQL（`route_json.budget` 五项完整），同期 SQLite 无该行；测试数据已清理
- 双库终态一致：users 6 / spots 3 / posts 3 / comments 11 / favorites 2 / trips 2，`status=0` 为 0

## 三、已知技术债清单

| 类别 | 项 | 影响 / 建议 |
|---|---|---|
| 代码规模 | `trip_service.py` 512 行、`Plan.vue` 575 行 | 抽 `distance_service` / 拆 Plan 子组件 |
| 接口口径 | `/spot/list`、`/spot/detail` 不返回 `lat/lng`、`ticket_price` | 前台无法展示坐标/票价；若答辩需展示，扩 schema 即可 |
| 距离一致性 | 逐对降级：部分 leg 真实 km、部分 mock（新增景点缺坐标时） | 建议在响应加 `distance_source` 标注；或整条路线统一口径 |
| 缓存失效 | `_AMAP_CACHE` 不感知坐标更新 | 改坐标后需重启或调 `clear_distance_cache()` |
| 预算兼容 | legacy `daily_average`（门票日均）与新 `daily_avg` 语义不同 | 论文中需说明，避免答辩歧义 |
| 前端体验 | 天数输入框仍可漂移（生成后改天数只改标签，保存值已用快照钉住） | 建议生成后禁用天数/单价输入 |
| 超时 | axios `timeout: 10000`，5+ 景点偏紧 | 提高至 20s 或按景点数动态 |
| 构建 | 单 chunk 832.83 kB 警告 | `manualChunks` 拆 echarts / element-plus |
| 测试 | 无 pytest 统一框架、无 CI，断言脚本手写 | 迁移 pytest + GitHub Actions |
| 安全 | CORS `*`、`allow_credentials=False`；`SECRET_KEY` 默认值 | 毕设可接受，生产需收紧 |
| 仓库 | `.opencode-data/opencode.db`(135MB)、`.omo/`(101 文件) 被跟踪；无 git remote | 建议 `git rm --cached` + `.gitignore`，并补远端 |
| 脚本风险 | `init_favorites.py` 破坏性（已加 `--yes`） | 建议再加环境白名单（禁止 prod） |
| 功能预留 | 游玩偏好未实现（已标记为预留扩展点，本期不开发） | 见 §五 扩展点 1 |

## 四、回滚方案（切回 SQLite）

**前提**：SQLite 源库 `backend/travel.db` 全程未改动，双库计数一致（6/3/3/11/2/2）。

```powershell
# 1) 改 backend/.env：注释 MySQL 行，启用 SQLite 行
#    DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/travel_bishe?charset=utf8mb4
DATABASE_URL=sqlite:///./travel.db

# 2) 重启后端（.env 不热重载）
cd D:\Users\zbb\Desktop\毕业设计AI\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 3) 验证
#    GET /api/v1/spot/list → 3 条；trips 2 条（'1'、'西湖'）
```

- **兜底恢复**：若 `travel.db` 损坏，用备份覆盖
  `Copy-Item backend\travel_backup_v09_20261026.db backend\travel.db`
- **注意**：`Float(53)` 对 SQLite 无副作用（REAL）；MySQL 数据保留不丢，可随时切回
- **注意**：`init_favorites.py` 现在必须带 `--yes` 才会清数据

## 五、答辩可口述扩展点（本次不开发）

1. **游玩偏好权重**（已标记预留）：`spots.tags` 已有自然/历史/城市标签 → 规划页加偏好多选 → 后端在边权引入 `w_pref × (1 − tag_match)`，或先按偏好打分裁剪候选集再进路径搜索；一句话要点："偏好不改图结构，只改边权，Dijkstra 复用"
2. **情感可视化**：现有 `/post/spot/{id}/sentiment` + 饼图 → 扩为按周情感趋势折线、关键词词云、路线级"情绪画像"；要点："已有情感分值，缺的是时间维聚合"
3. **图片上传**：`posts` 增 `cover_url`，后端 `UploadFile` 落 `static/uploads`（类型/大小校验），前端 `el-upload`；要点："先本地存储，云 OSS 只需换存储适配层"
4. **低成本加分项**：配置 `AMAP_KEY` 即从 mock 切真实距离（零代码）；行程导出 PDF；推荐冷启动（收藏+浏览加权）

---

**冻结声明**：v0.9 起停止新增功能与新需求；后续仅处理阻塞答辩的缺陷，并准备论文、截图与录屏。
