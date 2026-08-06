# 通维 AI-PM · PMBOK 第7版/第8版 知识体系覆盖度报告

- **编制日期**：2026-07-17
- **参考标准**：PMBOK Guide 第7版（12原则 + 8绩效域）+ 第8版新增内容
- **定位**：补充第6版的过程导向体系，对齐新版原则导向+价值导向框架

---

## TL;DR

| 维度 | 覆盖状态 |
|------|----------|
| 12 项项目管理原则 | ✅ **全覆盖**（系统能力直接或间接体现） |
| 8 大项目绩效域 | ✅ **全覆盖**（系统功能覆盖所有绩效域） |
| 第8版新增（AI/ESG/数据驱动） | ✅ **领先覆盖**（AI原生系统天然优势） |

---

## 一、12 项项目管理原则覆盖（第7版）

| # | 原则 | 系统体现 | 对应功能 |
|---|------|----------|----------|
| 1 | **Stewardship**（尽责服务） | RBAC权限、审计日志、安全合规 | auth, compliance, monitoring |
| 2 | **Team**（协作团队） | 项目成员管理、角色分配、团队沟通 | members, roles, messages |
| 3 | **Stakeholders**（干系人参与） | 干系人认证、通知、OKR对齐 | auth, notifications, okrs |
| 4 | **Value**（聚焦价值） | EVM挣值管理、商业价值追踪 | reports, budgets, evm |
| 5 | **Systems Thinking**（系统思考） | 项目组合管理、关联分析 | projects, portfolio, integrations |
| 6 | **Leadership**（领导力） | 项目管理授权、审批流 | approvals, change_control |
| 7 | **Tailoring**（裁剪） | 自定义字段、模板、灵活配置 | custom_fields, task_templates, llm_configs |
| 8 | **Quality**（质量） | 合规检查、质量标准、审计 | compliance, monitoring |
| 9 | **Complexity**（驾驭复杂性） | AI风险预测、多Agent协同 | predictions, multi_agent |
| 10 | **Risk**（优化风险） | 风险登记册、概率×影响矩阵、AI预警 | risk, predictions |
| 11 | **Adaptability & Resiliency**（适应性与韧性） | 自动化工作流、敏捷Sprint | automations, sprints |
| 12 | **Change**（驱动变革） | 变更控制、版本发布 | change_control, releases |

---

## 二、8 大绩效域覆盖（第7版）

| # | 绩效域 | 系统能力 | 对应模块 |
|---|--------|----------|----------|
| 1 | **Stakeholder**（干系人） | 用户认证、角色权限、通知、OKR | auth, roles, notifications, okrs |
| 2 | **Team**（团队） | 成员管理、团队沟通、角色分配 | members, messages, roles |
| 3 | **Development Approach & Life Cycle**（开发方法与生命周期） | Sprint/敏捷/混合支持 | sprints, releases, epics |
| 4 | **Planning**（规划） | AI-WBS、需求分析、路线图、任务模板 | ai_nlp, ai, roadmap, task_templates |
| 5 | **Project Work**（项目工作） | 任务执行、自动化、集成、评论 | tasks, automations, comments, integrations |
| 6 | **Delivery**（交付） | 版本发布、里程碑、交付物管理 | releases, epics, attachments |
| 7 | **Measurement**（测量） | EVM挣值、监测指标、健康检查 | reports, monitoring, health |
| 8 | **Uncertainty**（不确定性） | 风险管理、AI预测、复杂性分析 | risk, predictions, multi_agent |

---

## 三、PMBOK 第8版新增内容覆盖（2026）

第8版在第7版基础上重点强化了以下方向：

| 新增维度 | 系统能力 | 覆盖 |
|----------|----------|:----:|
| **AI & 自动化**（AI原生项目管理） | AI-WBS / Agent引擎 / 多Agent协同 / RAG知识库 | ⭐⭐⭐⭐⭐ |
| **数据驱动决策**（Data-driven Decision Making） | EVM实时计算 / AI预测 / 监控仪表盘 | ⭐⭐⭐⭐⭐ |
| **可持续发展 ESG**（环境/社会/治理） | 合规审计 / 安全治理 / 资源优化 | ⭐⭐⭐ |
| **商业敏锐度**（Business Acumen） | OKR对齐 / 项目管理计划 / 组合管理 | ⭐⭐⭐⭐ |
| **混合方法论**（Hybrid Methodologies） | 支持预测型 + 敏捷 + 混合项目类型 | ⭐⭐⭐⭐ |
| **数字转型**（Digital Transformation） | MCP协议 / Webhook / 开放API生态 | ⭐⭐⭐⭐ |

---

## 四、第6版 vs 第7版 vs 第8版 三重体系覆盖

```
第6版（过程导向）         第7版（原则导向）           第8版（未来导向）
─────────────────────  ─────────────────────       ─────────────────────
5 大过程组               12 项原则                   AI 原生能力
10 大知识领域             8 大绩效域                 数据驱动决策
49 个过程               价值交付系统                 ESG 可持续
ITTO（输入/工具/输出）    模型·方法·工件              数字转型

        ┌─────────────────────────────────────────┐
        │          通维 AI-PM 三重覆盖              │
        │  ✅ 55文件PMBOK标注（第6版过程映射）       │
        │  ✅ 第7版12原则+8绩效域映射                │
        │  ✅ 第8版 AI原生能力超前覆盖                │
        └─────────────────────────────────────────┘
```

## 五、与第6版标注的整合

系统中已存在的 `[PMBOK KA: xxx]` 标注（第6版知识领域）的基础上，新增：
- 每个路由文件的 docstring 补充 `[PMBOK 7th Principle: xxx | Domain: xxx]`
- 关键 AI 文件标注 `[PMBOK 8th: AI-Driven/Automation]`

### 标注示例

```python
"""risk - PMBOK KA: 风险管理 (Risk Management)
[PMBOK 7th Principle: Risk/Optimize Risk Responses | Domain: Uncertainty]
[PMBOK 8th: Data-Driven Risk Analytics]
对应PMI第6版标准：风险识别、定性/定量分析、风险应对、风险登记册
第7版原则：优化风险应对策略、驾驭不确定性
第8版增强：AI驱动的风险预测分析
"""
```
