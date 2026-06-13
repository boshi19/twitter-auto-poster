# Twitter 自动发布系统 — 实现计划书

> **For Hermes:** Use codex skill to implement this plan — `codex exec` in demo1 directory.

**Goal:** 使用 Python + Buffer GraphQL API 实现 Twitter 自动发布，每日3次，CSV 存储推文，GitHub Actions 持续运行。

**Architecture:**
- Python 脚本读取 `tweets.csv`，通过 Buffer GraphQL API (`https://api.buffer.com`) 发布推文
- GitHub Actions cron 每日触发3次（UTC: 01:00 / 06:00 / 13:00，对应北京时间 09:00 / 14:00 / 21:00）
- Buffer API Key 和 Channel ID 存储在 GitHub Secrets 中

**Tech Stack:** Python 3.11+, `requests`, Buffer GraphQL API, GitHub Actions

---

## 前置条件（用户需要手动完成）

1. 注册 Buffer 账号 → https://publish.buffer.com
2. 连接 Twitter/X 账号到 Buffer
3. 获取 API Key → https://publish.buffer.com/settings/api
4. 获取 Channel ID（运行 `get_channel.py` 查询）
5. 在 GitHub 仓库设置 Secrets：`BUFFER_API_KEY`、`BUFFER_CHANNEL_ID`

---

## Task 1: 初始化 Git 仓库

**Objective:** 在 demo1 目录创建 Git 仓库

**Step 1:**
```bash
cd C:/Users/Administrator/Desktop/demo1 && git init
```

---

## Task 2: 创建 tweets.csv

**Objective:** 创建推文数据文件

**File:** `tweets.csv`

```csv
id,text,scheduled_time,status
1,用 Buffer API + Python 自动发推，每天定时推送，完全自动化 🚀 #自动化 #Twitter,09:00,pending
2,持续学习才是最强的竞争力。今天你又学到了什么新东西？ #成长 #学习,14:00,pending
3,晚安！今天的努力是明天成功的基石 💪 #正能量 #晚安,21:00,pending
```

---

## Task 3: 创建 get_channel.py（辅助脚本）

**Objective:** 查询 Buffer 账号的 Organization ID 和 Channel ID

**File:** `get_channel.py`

```python
import os, requests, json

API_KEY = os.getenv("BUFFER_API_KEY")
if not API_KEY:
    print("Error: 请设置 BUFFER_API_KEY 环境变量")
    print("获取 API Key: https://publish.buffer.com/settings/api")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
ENDPOINT = "https://api.buffer.com"

# Step 1: Get organizations
org_query = "{ account { organizations { id name } } }"
org_resp = requests.post(ENDPOINT, headers=HEADERS, json={"query": org_query})
org_data = org_resp.json()

if "errors" in org_data:
    print(f"API 错误: {org_data['errors']}")
    exit(1)

orgs = org_data["data"]["account"]["organizations"]
print(f"找到 {len(orgs)} 个组织:\n")

for org in orgs:
    print(f"  组织: {org['name']} (ID: {org['id']})")
    
    # Step 2: Get channels for each org
    ch_query = f'{{ channels(input: {{ organizationId: "{org["id"]}" }}) {{ id name service }} }}'
    ch_resp = requests.post(ENDPOINT, headers=HEADERS, json={"query": ch_query})
    ch_data = ch_resp.json()
    
    channels = ch_data["data"]["channels"]
    for ch in channels:
        print(f"    -> {ch['service']}: {ch['name']} (ID: {ch['id']})")
    print()

print("请将你的 Twitter Channel ID 设置为 GitHub Secret: BUFFER_CHANNEL_ID")
```

---

## Task 4: 创建 buffer_poster.py（核心脚本）

**Objective:** 读取 CSV，找到 pending 推文，通过 Buffer API 发布

**File:** `buffer_poster.py`

```python
import csv, os, sys, requests
from datetime import datetime

# === 配置 ===
ENDPOINT = "https://api.buffer.com"
API_KEY = os.getenv("BUFFER_API_KEY")
CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")
CSV_FILE = os.path.join(os.path.dirname(__file__), "tweets.csv")

if not API_KEY:
    print("❌ 环境变量 BUFFER_API_KEY 未设置")
    sys.exit(1)
if not CHANNEL_ID:
    print("❌ 环境变量 BUFFER_CHANNEL_ID 未设置")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# === 读取 CSV ===
def read_tweets(filepath):
    tweets = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tweets.append(row)
    return tweets

# === 写入 CSV ===
def write_tweets(filepath, tweets):
    fieldnames = ["id", "text", "scheduled_time", "status"]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tweets)

# === 查找下一条待发送推文 ===
def find_next_pending(tweets):
    now = datetime.now().strftime("%H:%M")
    for t in tweets:
        if t["status"] == "pending" and t["scheduled_time"] <= now:
            return t
    return None

# === 通过 Buffer API 发布 ===
def post_to_buffer(text):
    mutation = """
    mutation {
      createPost(input: {
        text: "%s",
        channelId: "%s",
        schedulingType: automatic,
        mode: addToQueue
      }) {
        ... on PostActionSuccess {
          post { id text dueAt }
        }
        ... on MutationError {
          message
        }
      }
    }
    """ % (text.replace('"', '\\"'), CHANNEL_ID)
    
    resp = requests.post(ENDPOINT, headers=HEADERS, json={"query": mutation})
    data = resp.json()
    
    if "errors" in data:
        return {"success": False, "error": str(data["errors"])}
    
    result = data.get("data", {}).get("createPost", {})
    if "post" in result:
        return {"success": True, "post_id": result["post"]["id"], "due_at": result["post"]["dueAt"]}
    else:
        return {"success": False, "error": result.get("message", "未知错误")}

# === 主流程 ===
def main():
    print(f"[{datetime.now().isoformat()}] 开始执行推文发布任务...")
    
    tweets = read_tweets(CSV_FILE)
    tweet = find_next_pending(tweets)
    
    if not tweet:
        print("⏭️  没有待发送的推文（当前时间段无可发送推文）")
        return
    
    print(f"📤 正在发送推文: {tweet['text'][:50]}...")
    result = post_to_buffer(tweet["text"])
    
    if result["success"]:
        tweet["status"] = "sent"
        write_tweets(CSV_FILE, tweets)
        print(f"✅ 发送成功! Post ID: {result['post_id']}, 预定时间: {result['due_at']}")
    else:
        print(f"❌ 发送失败: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Task 5: 创建 requirements.txt

**Objective:** 声明 Python 依赖

**File:** `requirements.txt`

```
requests>=2.28.0
```

---

## Task 6: 创建 GitHub Actions Workflow

**Objective:** 配置每日3次自动运行

**File:** `.github/workflows/post.yml`

```yaml
name: Auto Post Tweets

on:
  schedule:
    # UTC 01:00 = 北京时间 09:00
    - cron: "0 1 * * *"
    # UTC 06:00 = 北京时间 14:00
    - cron: "0 6 * * *"
    # UTC 13:00 = 北京时间 21:00
    - cron: "0 13 * * *"
  workflow_dispatch:  # 允许手动触发

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Post Tweet
        env:
          BUFFER_API_KEY: ${{ secrets.BUFFER_API_KEY }}
          BUFFER_CHANNEL_ID: ${{ secrets.BUFFER_CHANNEL_ID }}
        run: python buffer_poster.py

      - name: Commit sent status
        if: success()
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add tweets.csv
          git diff --staged --quiet || git commit -m "chore: update tweet status [skip ci]"
          git push
```

---

## Task 7: 创建 README.md

**Objective:** 使用说明文档

**File:** `README.md`

```markdown
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

- `scheduled_time`: 北京时间（HH:MM），与 GitHub Actions 的3个时间点对应
- `status`: `pending`（待发送）/ `sent`（已发送）

### 5. 每日发送时间
| UTC | 北京时间 |
|-----|---------|
| 01:00 | 09:00 |
| 06:00 | 14:00 |
| 13:00 | 21:00 |

## 手动触发
在 GitHub Actions 页面点击 "Run workflow" 按钮即可手动执行。
```

---

## Task 8: 提交并推送到 GitHub

**Objective:** 首次提交并推送到远程仓库

```bash
git add -A
git commit -m "feat: Twitter auto-poster with Buffer API + GitHub Actions"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```
