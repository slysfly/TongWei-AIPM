#!/bin/bash
# 注意：请替换为有效的登录 token
TOKEN="<your-jwt-token-here>"

echo "=== AI Agent Execute ==="
curl -s -X POST "http://localhost:8000/api/v1/ai/agent/execute" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"text":"帮我看看有什么任务","project_id":null,"context":{}}' 2>&1

echo ""
echo "=== Multi-Agent GET workflows ==="
curl -s "http://localhost:8000/api/v1/multi_agent/workflows" -H "Authorization: Bearer $TOKEN" 2>&1

echo ""
echo "=== Agents ==="
curl -s "http://localhost:8000/api/v1/agents" -H "Authorization: Bearer $TOKEN" 2>&1
