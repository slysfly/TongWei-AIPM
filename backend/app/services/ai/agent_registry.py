"""
通维AI项目管理系统 - 统一 Agent 注册中心（单一真相源 / Single Source of Truth）

整合两大体系：
① 开箱领域 Agent  —— 源自 out_of_box_agents.DISPATCH（10 个：报告/EVM/风险/WBS/纪要/资源/质量/合规/健康/决策）
② PMBOK / CPMAI 过程 Agent —— 源自 pmbok_agents.PMBOK_REGISTRY（PMBOK 第6版49过程 + 第8版原则/绩效域/裁剪 + CPMAI 7阶段 + 可信AI）

设计目标：
- 系统中所有「可被 /agents 目录展示」「可被 /agents/run 驱动」「可被工作流编排调用」的 Agent，
  都以本模块为唯一真相源。后端 API 与前端面板均从这里派生，不再各自维护硬编码 catalog。
- 领域 Agent 的 id 采用历史稳定 key「report」（与 AgentSession 遥测标签、前端现状一致），
  历史别名「weekly_report」仍被接受（归一化为 report），保持向后兼容。
- PMBOK / CPMAI 过程 Agent 的 id 采用 "pmbok:<id>" 前缀（如 pmbok:4.1 / pmbok:TA1），
  与 workflow_orchestrator._run_step 既有约定一致。
- run_agent(...) 为统一执行入口：工作流编排与 /agents/run 共用，最终委托 out_of_box_agents.run_agent。

[AI Orchestration | Unified Agent Registry | Single Source of Truth]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.ai.out_of_box_agents import (
    DISPATCH,
    AGENT_INPUT_HINT,
    run_agent as _run_oob_agent,
)
from app.services.ai.pmbok_agents import (
    PROCESSES,
    get_pmbok_catalog,
    get_pmbok_catalog_grouped,
    PMBOK_REGISTRY,
    itto_to_structured,
    _slug,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 领域 Agent 展示元数据（单一维护点）
# id 与历史稳定 key 对齐（report，对应 AgentSession 遥测标签与前端现状）
# --------------------------------------------------------------------------- #
DOMAIN_AGENT_META: Dict[str, Dict[str, Any]] = {
    "report": {
        "name": "报告生成 Agent", "type": "report", "icon": "FileTextOutlined",
        "color": "#10B981", "category": "领域分析", "accuracy": 99,
        "description": "基于真实任务/风险/复盘统计自动生成日报/周报/项目状态报告",
    },
    "evm": {
        "name": "EVM 分析 Agent", "type": "analysis", "icon": "BarChartOutlined",
        "color": "#4F46E5", "category": "领域分析", "accuracy": 97,
        "description": "实时计算 PV/EV/AC/CPI/SPI 等挣值指标，自动识别成本与进度偏差",
    },
    "risk": {
        "name": "风险检测 Agent", "type": "risk", "icon": "WarningOutlined",
        "color": "#EF4444", "category": "领域分析", "accuracy": 93,
        "description": "扫描逾期/低进度/临近截止任务，生成概率×影响矩阵，推荐应对策略",
    },
    "meeting_minutes": {
        "name": "纪要转任务 Agent", "type": "meeting", "icon": "FileDoneOutlined",
        "color": "#0EA5E9", "category": "领域分析", "accuracy": 94,
        "description": "解析会议纪要/需求文档，自动提取行动项并创建任务",
    },
    "wbs": {
        "name": "WBS 生成 Agent", "type": "planning", "icon": "ThunderboltOutlined",
        "color": "#8B5CF6", "category": "领域分析", "accuracy": 95,
        "description": "AI 自动生成多级 WBS 分解并落库任务",
    },
    "resource": {
        "name": "资源优化 Agent", "type": "resource", "icon": "RobotOutlined",
        "color": "#F59E0B", "category": "领域分析", "accuracy": 91,
        "description": "分析资源负载热力，建议跨项目资源调配方案",
    },
    "quality": {
        "name": "质量检测 Agent", "type": "quality", "icon": "SafetyOutlined",
        "color": "#06B6D4", "category": "领域分析", "accuracy": 89,
        "description": "分析测试/缺陷趋势，提出质量门禁建议",
    },
    "compliance": {
        "name": "合规审计 Agent", "type": "compliance", "icon": "AimOutlined",
        "color": "#6366F1", "category": "领域分析", "accuracy": 96,
        "description": "按五大过程组审计项目流程合规性",
    },
    "health_check": {
        "name": "项目健康检查 Agent", "type": "analysis", "icon": "HeartOutlined",
        "color": "#F43F5E", "category": "领域分析", "accuracy": 92,
        "description": "综合检查项目的进度/成本/风险/质量状态，输出健康评分（0-100）",
    },
    "decision": {
        "name": "智能决策建议 Agent", "type": "analysis", "icon": "BulbOutlined",
        "color": "#8B5CF6", "category": "领域分析", "accuracy": 90,
        "description": "基于项目当前状态，给出3-5条可执行的决策建议",
    },
}

# 历史别名 → 规范 id（向后兼容；不会在目录中生成重复条目）
DOMAIN_ALIASES: Dict[str, str] = {
    "weekly_report": "report",
}

# 领域 Agent 默认结构化 ITTO（输入为必选物料，工具技术可勾选，输出为指定文件）
DOMAIN_AGENT_ITTO: Dict[str, Dict[str, List[str]]] = {
    "report": {"inputs": ["项目任务/风险/复盘真实数据", "统计范围(项目/全公司)"],
               "tools": ["数据聚合", "LLM 结构化润色", "三段式报告生成"],
               "outputs": ["项目状态报告文档"]},
    "evm": {"inputs": ["任务 PV/EV/AC 真实数据"],
            "tools": ["挣值计算", "偏差分析", "趋势预测"],
            "outputs": ["EVM 指标报告"]},
    "risk": {"inputs": ["项目任务清单", "历史风险登记"],
             "tools": ["逾期/低进度扫描", "概率×影响矩阵", "应对策略推荐"],
             "outputs": ["风险登记册更新", "风险报告"]},
    "meeting_minutes": {"inputs": ["会议纪要/需求文档文本"],
                        "tools": ["行动项抽取", "负责人识别", "任务创建"],
                        "outputs": ["任务清单", "行动项跟踪表"]},
    "wbs": {"inputs": ["项目目标/范围说明"],
            "tools": ["WBS 多级分解", "工作包生成", "落库"],
            "outputs": ["WBS 结构文档"]},
    "resource": {"inputs": ["资源负载数据", "任务分配数据"],
                 "tools": ["负载热力计算", "瓶颈识别", "调配建议"],
                 "outputs": ["资源优化建议"]},
    "quality": {"inputs": ["测试/缺陷数据"],
                "tools": ["质量趋势分析", "缺陷根因", "门禁建议"],
                "outputs": ["质量检查报告"]},
    "compliance": {"inputs": ["项目流程数据"],
                   "tools": ["五大过程组合规审计", "差距分析"],
                   "outputs": ["合规审计报告"]},
    "health_check": {"inputs": ["项目进度/成本/风险/质量数据"],
                    "tools": ["四维健康评分", "LLM 评估"],
                    "outputs": ["健康评分报告"]},
    "decision": {"inputs": ["项目当前状态快照"],
                 "tools": ["决策建模", "优先级排序", "影响评估"],
                 "outputs": ["决策建议清单"]},
}

# 反向映射（规范 id → 别名），用于补全 AGENT_INPUT_HINT 的查询
_CANON_TO_ALIAS: Dict[str, str] = {v: k for k, v in DOMAIN_ALIASES.items()}

# PMBOK kind → 注册中心 kind 标签
_PMBOK_KIND_MAP = {
    "process": "pmbok-process",
    "principle": "pmbok-principle",
    "domain": "pmbok-domain",
    "tailoring": "pmbok-tailoring",
    "cpmai": "cpmai-phase",
    "trustworthy": "cpmai-trustworthy",
}


@dataclass
class RegistryAgent:
    id: str
    name: str
    name_en: str
    kind: str            # domain | pmbok-process | pmbok-principle | pmbok-domain | pmbok-tailoring | cpmai-phase | cpmai-trustworthy
    category: str        # 前端分组标签
    source: str          # "domain" | "pmbok"
    type: str = "domain"  # 兼容旧字段（前端 AgentPanel 用）
    icon: str = "RobotOutlined"
    color: str = "#4F46E5"
    description: str = ""
    accuracy: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    input_hint: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)  # 过程组的 ITTO 等附加信息

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "name_en": self.name_en,
            "kind": self.kind,
            "category": self.category,
            "source": self.source,
            "type": self.type,
            "icon": self.icon,
            "color": self.color,
            "description": self.description,
            "accuracy": self.accuracy,
            "tags": self.tags,
            "inputHint": self.input_hint,
        }
        if self.extra:
            d["extra"] = self.extra
        return d


# --------------------------------------------------------------------------- #
# 构建统一注册表（模块加载时一次性完成）
# --------------------------------------------------------------------------- #
_REGISTRY: Dict[str, RegistryAgent] = {}


def _input_hint_for(aid: str) -> str:
    return AGENT_INPUT_HINT.get(aid) or AGENT_INPUT_HINT.get(_CANON_TO_ALIAS.get(aid, ""), "")


def _build_domain_agents() -> None:
    for aid in DISPATCH.keys():
        if aid in DOMAIN_ALIASES:           # 跳过别名（weekly_report），仅保留规范 key（report）
            continue
        meta = DOMAIN_AGENT_META.get(aid)
        if not meta:
            logger.warning("DISPATCH 中存在未在 DOMAIN_AGENT_META 登记的 Agent: %s（已跳过）", aid)
            continue
        _REGISTRY[aid] = RegistryAgent(
            id=aid,
            name=meta["name"],
            name_en=aid,
            kind="domain",
            category=meta.get("category", "领域分析"),
            source="domain",
            type=meta.get("type", "domain"),
            icon=meta.get("icon", "RobotOutlined"),
            color=meta.get("color", "#4F46E5"),
            description=meta.get("description", ""),
            accuracy=meta.get("accuracy"),
            tags=[meta.get("type", "domain")],
            input_hint=_input_hint_for(aid),
        )


def _build_pmbok_agents() -> None:
    for proc in PROCESSES:
        _REGISTRY[f"pmbok:{proc.id}"] = RegistryAgent(
            id=f"pmbok:{proc.id}",
            name=proc.name_cn,
            name_en=proc.name_en,
            kind=_PMBOK_KIND_MAP.get(proc.kind, "pmbok-process"),
            category=proc.category,
            source="pmbok",
            type="pmbok",
            description=proc.summary,
            accuracy=None,
            tags=[proc.process_group, proc.knowledge_area],
            input_hint="",
            extra={
                "process_group": proc.process_group,
                "knowledge_area": proc.knowledge_area,
                "inputs": proc.inputs,
                "tools": proc.tools,
                "outputs": proc.outputs,
                "v8": proc.v8,
            },
        )


_build_domain_agents()
_build_pmbok_agents()


# --------------------------------------------------------------------------- #
# 对外 API
# --------------------------------------------------------------------------- #

def list_agents(
    category: Optional[str] = None,
    source: Optional[str] = None,
    kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """返回统一 Agent 目录（可过滤）。"""
    items = [a.to_dict() for a in _REGISTRY.values()]
    if category:
        items = [i for i in items if i["category"] == category]
    if source:
        items = [i for i in items if i["source"] == source]
    if kind:
        items = [i for i in items if i["kind"] == kind]
    return items


def list_agents_grouped() -> Dict[str, Any]:
    """按 category 分组返回，便于前端做 Tab / 折叠面板。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for a in _REGISTRY.values():
        if a.category not in groups:
            groups[a.category] = []
            order.append(a.category)
        groups[a.category].append(a.to_dict())
    return {
        "groups": [
            {"category": c, "count": len(groups[c]), "items": groups[c]}
            for c in order
        ],
        "total": len(_REGISTRY),
    }


def list_categories() -> List[str]:
    seen: List[str] = []
    for a in _REGISTRY.values():
        if a.category not in seen:
            seen.append(a.category)
    return seen


def get_agent(agent_id: str) -> Optional[RegistryAgent]:
    return _REGISTRY.get(agent_id)


def is_registered(agent_id: str) -> bool:
    """该 Agent 是否可被工作流编排 / /agents/run 调用。"""
    if agent_id in _REGISTRY:
        return True
    # 历史别名也算已注册
    return agent_id in DOMAIN_ALIASES


def list_domain_ids() -> List[str]:
    return [a.id for a in _REGISTRY.values() if a.source == "domain"]


async def run_agent(
    agent_type: str,
    db: Any,
    user_id: str,
    project_id: Optional[str] = None,
    input_text: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """统一执行入口（工作流编排 / /agents/run 共用）。

    - 历史别名（weekly_report）归一化为规范 id（report）；
    - pmbok:<id> 与领域 key 最终委托 out_of_box_agents.run_agent 真实调度。
    """
    # 归一化历史别名
    if agent_type in DOMAIN_ALIASES:
        agent_type = DOMAIN_ALIASES[agent_type]
    return await _run_oob_agent(
        agent_type=agent_type,
        db=db,
        user_id=user_id,
        project_id=project_id,
        input_text=input_text,
        options=options,
    )


def _norm_item(item: Any, kind: str) -> Dict[str, Any]:
    """把任意（可能脏）结构项归一化为统一的六项字段。

    统一字段（输入/工具/输出完全一致）：
      key, label, optional, enabled, kind, template_prompt
    - enabled 表示该项是否被「勾选启用」参与本次运行；默认 True。
    - optional 表示该项是否「必需」(False) 或「可选」(True)，与 enabled 无直接关系。
    """
    if not isinstance(item, dict):
        item = {"label": str(item), "key": _slug(str(item))}
    d = {
        "key": item.get("key") or _slug(str(item.get("label", ""))),
        "label": item.get("label") or item.get("key") or "",
        "optional": bool(item.get("optional", False)) if kind in ("input", "output") else False,
        "enabled": bool(item.get("enabled", True)),
        "kind": item.get("kind") or ("file" if kind in ("input", "output") else "technique"),
        "template_prompt": item.get("template_prompt") or "",
    }
    return d


def _pmbok_raw_key(agent_id: str) -> Optional[str]:
    """归一化 PMBOK / CPMAI 过程 ID。

    兼容 ``pmbok:<id>`` 与原始 ``proc.id``（如 ``4.1`` / ``P0`` / ``C1``）两种写法，
    返回其在 PMBOK_REGISTRY 中的原始 key；若不是 PMBOK 过程则返回 None。
    保证两种写法映射到同一份 ITTO / override。
    """
    raw = agent_id.split(":", 1)[1] if agent_id.startswith("pmbok:") else agent_id
    return raw if raw in PMBOK_REGISTRY else None


def normalize_agent_id(agent_id: str) -> str:
    """把任意写法的 Agent ID 归一为规范形式。

    - PMBOK/CPMAI 过程（无论是否带 ``pmbok:`` 前缀）统一为 ``pmbok:<id>``；
    - 领域 Agent（report 等）保持原样。
    """
    raw = _pmbok_raw_key(agent_id)
    return f"pmbok:{raw}" if raw is not None else agent_id


def candidate_override_keys(agent_id: str) -> List[str]:
    """返回 override 存储可能使用的 key 候选（兼容 raw 与 ``pmbok:`` 两种写法）。

    用于「同一份覆盖」在不同 ID 写法下都能被命中。
    """
    raw = _pmbok_raw_key(agent_id)
    if raw is not None:
        return [f"pmbok:{raw}", raw]
    return [agent_id]


def get_structured_itto(agent_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """返回某 Agent 的结构化 ITTO（inputs/tools/outputs 均为结构化项）。

    优先级：个性化覆盖 > 领域 Agent 默认 ITTO > PMBOK 注册表。
    ID 归一化：``pmbok:<id>`` 与原始 ``<id>``（如 ``4.1``）都映射到同一份 ITTO / override。
    供「运行前物料检查」与「运行管线」统一读取。
    """
    # 延迟导入避免与 agent.py 循环依赖
    try:
        from app.api.v1.ai_routes.agent import _load_overrides
        all_ovr = _load_overrides()
    except Exception:  # noqa: BLE001
        all_ovr = {}
    # override 兼容：'pmbok:<id>' 与原始 '<id>' 两种 key 都能命中同一份覆盖
    ovr = next(
        (all_ovr[k] for k in candidate_override_keys(agent_id) if k in all_ovr),
        {},
    )
    # 优先使用前端保存的「完整结构化 ITTO」（含 optional / enabled 等可配置项）
    if ovr.get("inputs_struct") or ovr.get("tools_struct") or ovr.get("outputs_struct"):
        return {
            "inputs": [_norm_item(i, "input") for i in (ovr.get("inputs_struct") or [])],
            "tools": [_norm_item(i, "tool") for i in (ovr.get("tools_struct") or [])],
            "outputs": [_norm_item(i, "output") for i in (ovr.get("outputs_struct") or [])],
        }
    if ovr.get("inputs") or ovr.get("tools") or ovr.get("outputs"):
        return {
            "inputs": itto_to_structured("input", ovr.get("inputs") or []),
            "tools": itto_to_structured("tool", ovr.get("tools") or []),
            "outputs": itto_to_structured("output", ovr.get("outputs") or []),
        }
    # 领域 Agent 默认
    if agent_id in DOMAIN_AGENT_ITTO:
        d = DOMAIN_AGENT_ITTO[agent_id]
        return {
            "inputs": itto_to_structured("input", d["inputs"]),
            "tools": itto_to_structured("tool", d["tools"]),
            "outputs": itto_to_structured("output", d["outputs"]),
        }
    # PMBOK / CPMAI 过程（兼容 'pmbok:<id>' 与原始 '<id>' 两种写法）
    raw = _pmbok_raw_key(agent_id)
    if raw is not None:
        proc = PMBOK_REGISTRY.get(raw)
        if proc:
            return {
                "inputs": itto_to_structured("input", proc.inputs),
                "tools": itto_to_structured("tool", proc.tools),
                "outputs": itto_to_structured("output", proc.outputs),
            }
    return {"inputs": [], "tools": [], "outputs": []}


# 重新导出 PMBOK 目录函数，便于 API 层统一从本模块导入
__all__ = [
    "RegistryAgent",
    "list_agents",
    "list_agents_grouped",
    "list_categories",
    "get_agent",
    "is_registered",
    "list_domain_ids",
    "run_agent",
    "get_pmbok_catalog",
    "get_pmbok_catalog_grouped",
    "PMBOK_REGISTRY",
]
