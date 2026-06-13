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
print(f"找到 {len(orgs)} 个组织\n")

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
