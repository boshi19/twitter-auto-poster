# Twitter 自动发布系统

基于 Buffer API + GitHub Actions 的 Twitter 自动发布脚本。

## 架构

- `tweets.csv` — 推文数据存储
- `buffer_poster.py` — 核心发布脚本（调用 Buffer GraphQL API）
- `get_channel.py` — 查询 Channel ID 的辅助脚本
- `.github/workflows/post.yml` — GitHub Actions 每日3次自动运行

## 使用步骤

### 1. 获取 Buffer API Key
访问 https://publish.buffer.com/settings/api 获取 API Key

### 2. 获取 Channel ID
```bash
set BUFFER_API_KEY=你的API_Key
python get_channel.py
```

### 3. 设置 GitHub Secrets
在仓库 Settings → Secrets and variables → Actions 中添加：
- `BUFFER_API_KEY`
- `BUFFER_CHANNEL_ID`

### 4. 编辑推文
编辑 `tweets.csv`，格式：
```csv
id,text,scheduled_time,status
1,推文内容,09:00,pending
```

- `scheduled_time`: 北京时间（HH:MM），与 GitHub Actions 的 3 个时间点对应
- `status`: `pending`（待发送）/ `sent`（已发送）

### 5. 每日发送时间
| UTC | 北京时间 |
|-----|---------|
| 01:00 | 09:00 |
| 06:00 | 14:00 |
| 13:00 | 21:00 |

## 手动触发
在 GitHub Actions 页面点击 "Run workflow" 按钮即可手动执行。
