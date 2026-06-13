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
    for tweet in tweets:
        if tweet["status"] == "pending" and tweet["scheduled_time"] <= now:
            return tweet
    return None

# === 通过 Buffer GraphQL API 发推 ===
def post_to_buffer(text):
    mutation = """
    mutation {
      createPost(input: {
        text: "%s",
        channelIds: ["%s"],
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
        print("✅ 没有待发送的推文（当前时间段无可发送推文）")
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
