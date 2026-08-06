# 注意：请替换为有效的登录 token
TOKEN="<your-jwt-token-here>"

# List projects
curl -s "http://localhost:8000/api/v1/projects" -H "Authorization: Bearer $TOKEN"
echo "---"
# Test task creation (like calendar would)
curl -s -X POST "http://localhost:8000/api/v1/tasks/" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"name":"测试日历任务","project_id":"550e8400-e29b-41d4-a716-446655440000","priority":3,"status":"todo","planned_end":"2026-07-17"}'
