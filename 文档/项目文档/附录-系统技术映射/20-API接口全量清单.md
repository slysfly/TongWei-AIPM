# 20 · API 接口（路由）全量清单

> 本清单由脚本扫描 `backend/app/api/routers.py` 与 `backend/app/api/v1/*.py` 真实注册关系生成。
> 系统共 **56 个路由模块**，**383 个 HTTP 端点**（另含 1 个 WebSocket 模块 `ws`，无 HTTP 路由）。
> 全部挂载于统一前缀 `/api/v1`。旧版本文档写"40 模块 / 285+ 端点"系早期口径，本次按真实代码更正为 **56 模块 / 383 端点**。

路由注册方式：`api_router.include_router(<module>.router, prefix="...")`，前缀为空串的模块其路径已在文件内写成完整子路径。

---

## 1. auth — `/auth` · 4
- POST   /api/v1/auth/register
- POST   /api/v1/auth/login
- GET    /api/v1/auth/me
- POST   /api/v1/auth/refresh

## 2. projects — `/projects` · 6
- POST   /api/v1/projects/
- GET    /api/v1/projects/
- GET    /api/v1/projects/{project_id}
- PUT    /api/v1/projects/{project_id}
- DELETE /api/v1/projects/{project_id}
- GET    /api/v1/projects/{project_id}/statistics

## 3. tasks — `/tasks` · 7
- POST   /api/v1/tasks/
- GET    /api/v1/tasks/
- GET    /api/v1/tasks/{task_id}
- PUT    /api/v1/tasks/{task_id}
- DELETE /api/v1/tasks/{task_id}
- POST   /api/v1/tasks/{task_id}/dependencies
- GET    /api/v1/tasks/{task_id}/subtasks

## 4. ai — `/ai` · 5
- POST   /api/v1/ai/generate-wbs
- POST   /api/v1/ai/chat
- POST   /api/v1/ai/chat/stream
- POST   /api/v1/ai/analyze-project/{project_id}
- POST   /api/v1/ai/predict-risk/{project_id}

## 5. ai_agent — `/ai` · 6
- POST   /api/v1/ai/agent/execute
- POST   /api/v1/ai/agent/chat
- GET    /api/v1/ai/agent/sessions/{session_id}/history
- POST   /api/v1/ai/agent/sessions
- GET    /api/v1/ai/agent/sessions
- DELETE /api/v1/ai/agent/sessions/{session_id}

## 6. custom_fields — `/custom-fields` · 7
- POST   /api/v1/custom-fields/
- GET    /api/v1/custom-fields/
- GET    /api/v1/custom-fields/{field_id}
- PUT    /api/v1/custom-fields/{field_id}
- DELETE /api/v1/custom-fields/{field_id}
- POST   /api/v1/custom-fields/{field_id}/values
- GET    /api/v1/custom-fields/by-entity/{entity_type}/{entity_id}

## 7. automations — `/automations` · 7
- POST   /api/v1/automations/
- GET    /api/v1/automations/
- GET    /api/v1/automations/{rule_id}
- PUT    /api/v1/automations/{rule_id}
- DELETE /api/v1/automations/{rule_id}
- PUT    /api/v1/automations/{rule_id}/toggle
- POST   /api/v1/automations/{rule_id}/test

## 8. comments — （无前缀，挂 tasks 下）· 5
- POST   /api/v1/tasks/{task_id}/comments
- GET    /api/v1/tasks/{task_id}/comments
- PUT    /api/v1/comments/{comment_id}
- DELETE /api/v1/comments/{comment_id}
- POST   /api/v1/comments/{comment_id}/reply

## 9. notifications — `/notifications` · 5
- GET    /api/v1/notifications/
- PUT    /api/v1/notifications/{notification_id}/read
- PUT    /api/v1/notifications/read-all
- GET    /api/v1/notifications/unread-count
- DELETE /api/v1/notifications/{notification_id}

## 10. attachments — `/attachments` · 4
- POST   /api/v1/attachments/upload
- GET    /api/v1/attachments/{attachment_id}/download
- GET    /api/v1/attachments/tasks/{task_id}/attachments
- DELETE /api/v1/attachments/{attachment_id}

## 11. webhooks — （无前缀）· 7
- POST   /api/v1/              （接收第三方事件根路径）
- GET    /api/v1/{webhook_id}
- PUT    /api/v1/{webhook_id}
- DELETE /api/v1/{webhook_id}
- POST   /api/v1/{webhook_id}/test
- GET    /api/v1/{webhook_id}/deliveries

## 12. roles — （无前缀）· 6
- POST   /api/v1/
- GET    /api/v1/
- GET    /api/v1/{role_id}
- PUT    /api/v1/{role_id}
- DELETE /api/v1/{role_id}
- GET    /api/v1/permissions/all

## 13. members — （无前缀）· 6
- POST   /api/v1/
- GET    /api/v1/
- GET    /api/v1/{user_id}
- PUT    /api/v1/{user_id}
- DELETE /api/v1/{user_id}
- GET    /api/v1/{user_id}/permissions

## 14. reports — （无前缀）· 13
- GET    /api/v1/daily
- GET    /api/v1/weekly
- GET    /api/v1/projects/{project_id}/status
- POST   /api/v1/daily/send
- GET    /api/v1/templates
- GET    /api/v1/project-progress
- GET    /api/v1/burndown
- GET    /api/v1/velocity
- GET    /api/v1/cumulative-flow
- GET    /api/v1/evm
- GET    /api/v1/resource-utilization
- GET    /api/v1/risk-trend
- GET    /api/v1/export

## 15. messages — （无前缀）· 11
- GET    /api/v1/channels
- POST   /api/v1/channels
- GET    /api/v1/channels/{channel_id}/messages
- POST   /api/v1/channels/{channel_id}/messages
- PUT    /api/v1/messages/{message_id}
- DELETE /api/v1/messages/{message_id}
- POST   /api/v1/messages/{message_id}/reactions
- DELETE /api/v1/messages/{message_id}/reactions/{emoji}
- POST   /api/v1/channels/{channel_id}/members
- PUT    /api/v1/channels/{channel_id}/read
- GET    /api/v1/channels/{channel_id}/members

## 16. ws — （WebSocket）· 0 HTTP
- 说明：通过 WebSocket 端点提供实时消息/通知推送，无 REST 路由。

## 17. integrations — （无前缀）· 9
- GET    /api/v1/
- GET    /api/v1/{provider}/oauth-url
- POST   /api/v1/{provider}/connect
- POST   /api/v1/{provider}/disconnect
- GET    /api/v1/{provider}/status
- POST   /api/v1/{provider}/sync
- POST   /api/v1/{provider}/webhook
- POST   /api/v1/{provider}/action/{action}
- POST   /api/v1/inbound/agent

## 18. wiki — `/wiki` · 20
- POST   /api/v1/wiki/spaces
- GET    /api/v1/wiki/spaces
- GET    /api/v1/wiki/spaces/{space_id}
- PUT    /api/v1/wiki/spaces/{space_id}
- DELETE /api/v1/wiki/spaces/{space_id}
- POST   /api/v1/wiki/spaces/{space_id}/pages
- GET    /api/v1/wiki/spaces/{space_id}/pages
- GET    /api/v1/wiki/spaces/{space_id}/pages/tree
- GET    /api/v1/wiki/pages/{page_id}
- PUT    /api/v1/wiki/pages/{page_id}
- DELETE /api/v1/wiki/pages/{page_id}
- GET    /api/v1/wiki/pages/{page_id}/versions
- POST   /api/v1/wiki/pages/{page_id}/versions/{version_id}/restore
- GET    /api/v1/wiki/pages/{page_id}/comments
- POST   /api/v1/wiki/pages/{page_id}/comments
- PUT    /api/v1/wiki/comments/{comment_id}
- DELETE /api/v1/wiki/comments/{comment_id}
- POST   /api/v1/wiki/pages/{page_id}/lock
- DELETE /api/v1/wiki/pages/{page_id}/lock
- GET    /api/v1/wiki/search

## 19. search — （无前缀）· 2
- GET    /api/v1/search
- GET    /api/v1/search/suggest

## 20. monitoring — （无前缀）· 4
- GET    /api/v1/monitoring/metrics
- GET    /api/v1/monitoring/health
- GET    /api/v1/monitoring/slow-queries
- GET    /api/v1/monitoring/errors

## 21. compliance — `/compliance` · 18
- POST   /api/v1/compliance/policies
- GET    /api/v1/compliance/policies
- GET    /api/v1/compliance/policies/{policy_id}
- PUT    /api/v1/compliance/policies/{policy_id}
- DELETE /api/v1/compliance/policies/{policy_id}
- POST   /api/v1/compliance/controls
- GET    /api/v1/compliance/controls
- GET    /api/v1/compliance/controls/{control_id}
- PUT    /api/v1/compliance/controls/{control_id}
- DELETE /api/v1/compliance/controls/{control_id}
- POST   /api/v1/compliance/controls/{control_id}/test
- POST   /api/v1/compliance/audits
- GET    /api/v1/compliance/audits
- GET    /api/v1/compliance/audits/{audit_id}
- POST   /api/v1/compliance/evidences
- GET    /api/v1/compliance/evidences
- GET    /api/v1/compliance/dashboard
- GET    /api/v1/compliance/reports/summary

## 22. approvals — `/approvals` · 20
- POST   /api/v1/approvals/flows
- GET    /api/v1/approvals/flows
- GET    /api/v1/approvals/flows/{flow_id}
- PUT    /api/v1/approvals/flows/{flow_id}
- DELETE /api/v1/approvals/flows/{flow_id}
- POST   /api/v1/approvals/flows/{flow_id}/activate
- POST   /api/v1/approvals/flows/{flow_id}/deactivate
- POST   /api/v1/approvals/requests
- GET    /api/v1/approvals/requests
- GET    /api/v1/approvals/requests/{instance_id}
- GET    /api/v1/approvals/pending
- POST   /api/v1/approvals/steps/{step_id}/approve
- POST   /api/v1/approvals/steps/{step_id}/reject
- POST   /api/v1/approvals/steps/{step_id}/transfer
- GET    /api/v1/approvals/processed
- GET    /api/v1/approvals/dashboard
- POST   /api/v1/approvals/delegates
- GET    /api/v1/approvals/delegates
- PUT    /api/v1/approvals/delegates/{delegate_id}
- DELETE /api/v1/approvals/delegates/{delegate_id}

## 23. exports — `/imports`（含导出）· 6
- GET    /api/v1/imports/projects/{project_id}/tasks/excel
- GET    /api/v1/imports/projects/{project_id}/tasks/csv
- GET    /api/v1/imports/projects/{project_id}/report/pdf
- POST   /api/v1/imports/tasks
- POST   /api/v1/imports/tasks/preview
- GET    /api/v1/imports/template

## 24. budgets — （无前缀）· 18
- POST   /api/v1/projects/{project_id}/budget
- GET    /api/v1/projects/{project_id}/budget
- GET    /api/v1/budgets/{budget_id}
- PUT    /api/v1/budgets/{budget_id}
- DELETE /api/v1/budgets/{budget_id}
- GET    /api/v1/budgets/{budget_id}/categories
- POST   /api/v1/budgets/{budget_id}/categories
- GET    /api/v1/budgets/categories/{category_id}
- PUT    /api/v1/budgets/categories/{category_id}
- DELETE /api/v1/budgets/categories/{category_id}
- GET    /api/v1/projects/{project_id}/costs
- POST   /api/v1/projects/{project_id}/costs
- GET    /api/v1/costs/{cost_id}
- PUT    /api/v1/costs/{cost_id}
- DELETE /api/v1/costs/{cost_id}
- GET    /api/v1/projects/{project_id}/budget/report
- GET    /api/v1/projects/{project_id}/budget/trend
- GET    /api/v1/projects/{project_id}/budget/overview

## 25. recurring_tasks — `/recurring-tasks` · 9
- POST   /api/v1/recurring-tasks/
- GET    /api/v1/recurring-tasks/
- GET    /api/v1/recurring-tasks/{task_id}
- PUT    /api/v1/recurring-tasks/{task_id}
- DELETE /api/v1/recurring-tasks/{task_id}
- POST   /api/v1/recurring-tasks/{task_id}/toggle
- POST   /api/v1/recurring-tasks/{task_id}/run-now
- GET    /api/v1/recurring-tasks/{task_id}/instances
- POST   /api/v1/recurring-tasks/preview

## 26. app_market — `/app-market` · 8
- GET    /api/v1/app-market/plugins
- GET    /api/v1/app-market/plugins/{plugin_id}
- POST   /api/v1/app-market/plugins
- POST   /api/v1/app-market/plugins/{plugin_id}/install
- POST   /api/v1/app-market/plugins/{plugin_id}/uninstall
- POST   /api/v1/app-market/plugins/{plugin_id}/rate
- GET    /api/v1/app-market/installed
- PUT    /api/v1/app-market/installations/{installation_id}/config

## 27. llm_configs — `/llm-configs` · 7
- GET    /api/v1/llm-configs/
- POST   /api/v1/llm-configs/
- PUT    /api/v1/llm-configs/{config_id}
- DELETE /api/v1/llm-configs/{config_id}
- POST   /api/v1/llm-configs/{config_id}/set-default
- POST   /api/v1/llm-configs/{config_id}/test
- GET    /api/v1/llm-configs/providers

## 28. nlp_query — `/nlp-query` · 3
- POST   /api/v1/nlp-query/execute
- POST   /api/v1/nlp-query/validate
- GET    /api/v1/nlp-query/examples

## 29. mcp — （无前缀，MCP 协议）· 9
- POST   /api/v1/initialize
- POST   /api/v1/tools/list
- POST   /api/v1/tools/call
- POST   /api/v1/resources/list
- POST   /api/v1/resources/read
- POST   /api/v1/prompts/list
- POST   /api/v1/prompts/get
- GET    /api/v1/sse
- GET    /api/v1/status

## 30. multi_agent — （无前缀）· 7
- POST   /api/v1/teams
- POST   /api/v1/teams/{team_id}/run
- GET    /api/v1/teams/{team_id}/status
- GET    /api/v1/teams/{team_id}/logs
- GET    /api/v1/teams
- DELETE /api/v1/teams/{team_id}
- GET    /api/v1/teams/{team_id}/agents

## 31. scheduled_jobs — `/scheduled-jobs` · 10
- POST   /api/v1/scheduled-jobs/
- GET    /api/v1/scheduled-jobs/
- GET    /api/v1/scheduled-jobs/presets
- GET    /api/v1/scheduled-jobs/{job_id}
- PUT    /api/v1/scheduled-jobs/{job_id}
- DELETE /api/v1/scheduled-jobs/{job_id}
- POST   /api/v1/scheduled-jobs/{job_id}/run-now
- POST   /api/v1/scheduled-jobs/{job_id}/pause
- POST   /api/v1/scheduled-jobs/{job_id}/resume
- GET    /api/v1/scheduled-jobs/{job_id}/logs

## 32. zapier — （无前缀）· 9
- GET    /api/v1/triggers
- GET    /api/v1/sample-data
- POST   /api/v1/auth
- POST   /api/v1/subscribe
- POST   /api/v1/unsubscribe
- POST   /api/v1/webhook
- GET    /api/v1/ping
- POST   /api/v1/test-connection
- GET    /api/v1/polling/{trigger_id}

## 33. forms — `/forms` · 15
- POST   /api/v1/forms/templates
- GET    /api/v1/forms/templates
- GET    /api/v1/forms/templates/{template_id}
- PUT    /api/v1/forms/templates/{template_id}
- DELETE /api/v1/forms/templates/{template_id}
- POST   /api/v1/forms/templates/{template_id}/publish
- POST   /api/v1/forms/templates/{template_id}/unpublish
- POST   /api/v1/forms/templates/{template_id}/submit
- GET    /api/v1/forms/templates/{template_id}/submissions
- GET    /api/v1/forms/submissions/{submission_id}
- PUT    /api/v1/forms/submissions/{submission_id}
- GET    /api/v1/forms/templates/{template_id}/stats
- POST   /api/v1/forms/templates/{template_id}/export
- GET    /api/v1/forms/templates/{template_id}/embed
- GET    /api/v1/forms/embed/{source_type}/{source_id}

## 34. knowledge_base — （无前缀）· 16
- GET    /api/v1/knowledge-bases
- POST   /api/v1/knowledge-bases
- GET    /api/v1/knowledge-bases/{kb_id}
- PUT    /api/v1/knowledge-bases/{kb_id}
- DELETE /api/v1/knowledge-bases/{kb_id}
- GET    /api/v1/knowledge-bases/{kb_id}/documents
- POST   /api/v1/knowledge-bases/{kb_id}/documents
- POST   /api/v1/knowledge-bases/{kb_id}/documents/upload
- GET    /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}
- DELETE /api/v1/knowledge-bases/documents/{doc_id}
- POST   /api/v1/knowledge-bases/{kb_id}/search
- POST   /api/v1/knowledge-bases/search/multi
- POST   /api/v1/knowledge-bases/rag/context
- GET    /api/v1/knowledge-bases/{kb_id}/documents/{doc_id}/chunks
- POST   /api/v1/knowledge-bases/{kb_id}/qa
- POST   /api/v1/knowledge-bases/qa

## 35. okrs — （无前缀）· 3
- GET    /api/v1/{okr_id}
- PUT    /api/v1/{okr_id}
- DELETE /api/v1/{okr_id}

## 36. documents — （无前缀）· 3
- GET    /api/v1/{doc_id}
- PUT    /api/v1/{doc_id}
- DELETE /api/v1/{doc_id}

## 37. whiteboards — （无前缀）· 3
- GET    /api/v1/{board_id}
- PUT    /api/v1/{board_id}
- DELETE /api/v1/{board_id}

## 38. risk — （无前缀）· 3
- GET    /api/v1/{risk_id}
- PUT    /api/v1/{risk_id}
- DELETE /api/v1/{risk_id}

## 39. resources — （无前缀）· 2
- PUT    /api/v1/{res_id}
- DELETE /api/v1/{res_id}

## 40. system_llm_config — `/system` · 7
- GET    /api/v1/system/llm-config
- PUT    /api/v1/system/llm-config
- POST   /api/v1/system/llm-config/test
- GET    /api/v1/system/llm-config/providers
- POST   /api/v1/system/llm-config/sync-openclaw
- GET    /api/v1/system/openclaw-config
- PUT    /api/v1/system/openclaw-config

## 41. openclaw — `/openclaw` · 2
- POST   /api/v1/openclaw/assistant/chat
- GET    /api/v1/openclaw/status

## 42. ai_assist — `/ai` · 1
- POST   /api/v1/ai/assist-fill

## 43. api_keys — `/system` · 3
- POST   /api/v1/system/api-keys
- GET    /api/v1/system/api-keys
- DELETE /api/v1/system/api-keys/{key_id}

## 44. external — `/external` · 5
- GET    /api/v1/external/projects
- POST   /api/v1/external/projects
- GET    /api/v1/external/projects/{project_id}/tasks
- POST   /api/v1/external/tasks
- POST   /api/v1/external/ai/assistant

## 45. lessons — （无前缀）· 5
- GET    /api/v1/{lesson_id}
- PUT    /api/v1/{lesson_id}
- DELETE /api/v1/{lesson_id}
- POST   /api/v1/{lesson_id}/archive
- POST   /api/v1/archive-all

## 46. change_control — （无前缀）· 3
- GET    /api/v1/{change_id}
- PUT    /api/v1/{change_id}
- DELETE /api/v1/{change_id}

## 47. roadmap — （无前缀）· 3
- GET    /api/v1/{item_id}
- PUT    /api/v1/{item_id}
- DELETE /api/v1/{item_id}

## 48. sprints — `/sprints` · 10
- POST   /api/v1/sprints/
- GET    /api/v1/sprints/
- GET    /api/v1/sprints/{sprint_id}
- PUT    /api/v1/sprints/{sprint_id}
- DELETE /api/v1/sprints/{sprint_id}
- POST   /api/v1/sprints/{sprint_id}/start
- POST   /api/v1/sprints/{sprint_id}/complete
- POST   /api/v1/sprints/{sprint_id}/tasks
- DELETE /api/v1/sprints/{sprint_id}/tasks/{task_id}
- GET    /api/v1/sprints/{sprint_id}/report

## 49. epics — `/epics` · 8
- POST   /api/v1/epics/
- GET    /api/v1/epics/
- GET    /api/v1/epics/{epic_id}
- PUT    /api/v1/epics/{epic_id}
- DELETE /api/v1/epics/{epic_id}
- POST   /api/v1/epics/{epic_id}/tasks
- DELETE /api/v1/epics/{epic_id}/tasks/{task_id}
- POST   /api/v1/epics/{epic_id}/progress

## 50. releases — `/releases` · 9
- POST   /api/v1/releases/
- GET    /api/v1/releases/
- GET    /api/v1/releases/{release_id}
- PUT    /api/v1/releases/{release_id}
- DELETE /api/v1/releases/{release_id}
- POST   /api/v1/releases/{release_id}/tasks
- DELETE /api/v1/releases/{release_id}/tasks/{task_id}
- POST   /api/v1/releases/{release_id}/publish
- POST   /api/v1/releases/{release_id}/archive

## 51. task_templates — `/task-templates` · 8
- POST   /api/v1/task-templates/
- GET    /api/v1/task-templates/
- GET    /api/v1/task-templates/{template_id}
- PUT    /api/v1/task-templates/{template_id}
- DELETE /api/v1/task-templates/{template_id}
- POST   /api/v1/task-templates/{template_id}/create-task
- POST   /api/v1/task-templates/from-task
- POST   /api/v1/task-templates/{template_id}/copy

## 52. predictions — （无前缀）· 4
- GET    /api/v1/projects/{project_id}/health
- GET    /api/v1/projects/{project_id}/completion
- GET    /api/v1/sprints/{sprint_id}/risk
- GET    /api/v1/dashboard

## 53. ai_nlp — （无前缀）· 6
- POST   /api/v1/parse-task
- POST   /api/v1/create-task
- POST   /api/v1/decompose-requirement
- POST   /api/v1/decompose-requirement/confirm
- POST   /api/v1/estimate-task
- GET    /api/v1/estimate-project/{project_id}

## 54. agents — （无前缀）· 3
- GET    /api/v1/agents
- POST   /api/v1/agents/run
- GET    /api/v1/agents/runs

## 55. agent_workflow — （无前缀）· 1
- POST   /api/v1/workflow/run

## 56. methodology — （无前缀）· 2
- GET    /api/v1/templates
- POST   /api/v1/instantiate

---

> 合计：**56 个路由模块 · 383 个 HTTP 端点 + 1 个 WebSocket 模块**。所有端点挂载于 `/api/v1`。
> 校验方式：扫描 `routers.py` 的 `include_router` 注册链 + 各模块 `@router.{method}` 装饰器，与运行实例实际注册一致。
