import React, { useState, useCallback, useMemo, useEffect } from "react";
import {
  Card, Typography, Button, Space, App, Tag, Modal, Input,
  Select, Progress, Empty, List, Popconfirm, Spin, Segmented, Drawer, Tooltip,
} from "antd";
import {
  PlayCircleOutlined, SaveOutlined, DeleteOutlined,
  ReloadOutlined, ApartmentOutlined, PlusOutlined,
  LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined,
  FolderOpenOutlined, ThunderboltOutlined,
  BarChartOutlined, WarningOutlined, RobotOutlined, SafetyOutlined,
  AimOutlined, FileTextOutlined, FileDoneOutlined, ClearOutlined,
  PartitionOutlined, CompassOutlined, NodeIndexOutlined,
  HeartOutlined, BulbOutlined, SearchOutlined, SettingOutlined,
  HistoryOutlined, SwapOutlined, EyeOutlined,
} from "@ant-design/icons";
import {
  ReactFlow, Background, Controls, MiniMap, ReactFlowProvider,
  useNodesState, useEdgesState, addEdge, Handle, Position,
  useReactFlow, MarkerType,
  type Node, type Edge, type NodeProps, type Connection,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "framer-motion";
import { workflowApi, projectApi, agentApi } from "../api";

const { Text } = Typography;
const PRIMARY = "#4F46E5";

// ─────────────────────────────────────────────────────────────────────────────
// 类型定义
// ─────────────────────────────────────────────────────────────────────────────

type NodeStatus = "idle" | "running" | "success" | "error";

interface AgentNodeData {
  agentType: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  status: NodeStatus;
  // 新增：节点级运行配置（支撑上游输出→下游输入的精确绑定）
  userInput: string;                 // 内联补充输入文本
  selectedTools: string[];           // 勾选的工具技术 key
  inputMapping: Record<string, string>; // {输入槽key: 上游节点id}
}

type AgentNode = Node<AgentNodeData>;

interface LogEntry {
  id: string;
  time: string;
  label: string;
  message: string;
  level: "info" | "success" | "error";
}

/** 统一注册中心返回的 Agent 条目 */
interface RegistryAgentItem {
  id: string;
  name: string;
  name_en: string;
  kind: string;
  category: string;
  source: string;
  type: string;
  icon: string;
  color: string;
  description: string;
  accuracy: number | null;
  tags: string[];
  inputHint: string;
  extra?: {
    process_group?: string;
    knowledge_area?: string;
    inputs?: string[];
    tools?: string[];
    outputs?: string[];
    v8?: string;
  };
}

/** prepare 端点返回的结构化 ITTO 槽位 */
interface SlotItem {
  key: string;
  label: string;
  optional: boolean;
  enabled: boolean;
  kind: string;
  exists?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// 图标 / 配色映射
// ─────────────────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ComponentType<any>> = {
  FileTextOutlined, BarChartOutlined, WarningOutlined, RobotOutlined, ThunderboltOutlined,
  SafetyOutlined, AimOutlined, FileDoneOutlined, HeartOutlined, BulbOutlined,
  PartitionOutlined, CompassOutlined, ApartmentOutlined, NodeIndexOutlined,
};

/** PMBOK 各体系 → 代表图标（注册中心默认 icon 为 RobotOutlined，这里按体系区分更直观） */
const CAT_ICON: Record<string, React.ComponentType<any>> = {
  "PMBOK第6版·49过程": PartitionOutlined,
  "PMBOK第8版·原则": CompassOutlined,
  "PMBOK第8版·绩效域": ApartmentOutlined,
  "PMBOK第8版·裁剪": NodeIndexOutlined,
  "CPMAI·AI项目管理阶段": RobotOutlined,
  "CPMAI·可信AI框架": SafetyOutlined,
  "领域分析": ThunderboltOutlined,
};

/** PMBOK 各体系 → 品牌色 */
const CAT_COLOR: Record<string, string> = {
  "PMBOK第6版·49过程": "#4F46E5",
  "PMBOK第8版·原则": "#10B981",
  "PMBOK第8版·绩效域": "#6366F1",
  "PMBOK第8版·裁剪": "#06B6D4",
  "CPMAI·AI项目管理阶段": "#F59E0B",
  "CPMAI·可信AI框架": "#EF4444",
  "领域分析": "#4F46E5",
};

/** 默认画布种子（8 个领域 Agent，id 与注册中心对齐） */
const SEED_DOMAIN_IDS: { id: string; name: string; description: string; icon: React.ComponentType; color: string }[] = [
  { id: "wbs",        name: "WBS分解",   description: "AI 自动生成多级工作分解结构",   icon: ThunderboltOutlined, color: "#4F46E5" },
  { id: "evm",        name: "挣值管理",   description: "计算 PV/EV/AC 与 CPI/SPI 指标",  icon: BarChartOutlined,   color: "#6366F1" },
  { id: "risk",       name: "风险预测",   description: "扫描进度偏差，生成风险矩阵",     icon: WarningOutlined,    color: "#818CF8" },
  { id: "resource",   name: "资源优化",   description: "分析资源负载，建议调配方案",     icon: RobotOutlined,      color: "#4338CA" },
  { id: "quality",    name: "质量保障",   description: "分析缺陷趋势，提出质量门禁",     icon: SafetyOutlined,     color: "#7C3AED" },
  { id: "compliance", name: "合规审查",   description: "按过程组审计流程合规性",         icon: AimOutlined,        color: "#6D28D9" },
  { id: "report",     name: "报告生成",   description: "自动生成日报/周报/状态报告",     icon: FileTextOutlined,   color: "#4F46E5" },
  { id: "meeting_minutes", name: "会议纪要", description: "解析纪要，提取行动项与待办", icon: FileDoneOutlined,   color: "#8B5CF6" },
];

let _counter = 0;
const uid = (prefix: string) => `${prefix}_${Date.now()}_${_counter++}`;

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// ─────────────────────────────────────────────────────────────────────────────
// 自定义节点（含 Handle 连接点 + framer-motion 状态微动效 + 配置指示点）
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_META: Record<NodeStatus, { color: string; text: string; icon: React.ReactNode }> = {
  idle:    { color: "#94A3B8", text: "待运行", icon: <LoadingOutlined style={{ opacity: 0 }} /> },
  running: { color: "#F59E0B", text: "运行中", icon: <LoadingOutlined spin /> },
  success: { color: "#10B981", text: "成功",   icon: <CheckCircleOutlined /> },
  error:   { color: "#EF4444", text: "失败",   icon: <CloseCircleOutlined /> },
};

const StatusBadge: React.FC<{ status: NodeStatus }> = ({ status }) => {
  const m = STATUS_META[status];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: 10, color: m.color, fontWeight: 600,
      background: `${m.color}1A`, padding: "2px 6px", borderRadius: 8,
    }}>
      {m.icon}{m.text}
    </span>
  );
};

const hasConfig = (d: AgentNodeData) =>
  !!(d.userInput && d.userInput.trim()) ||
  (d.selectedTools && d.selectedTools.length > 0) ||
  (d.inputMapping && Object.keys(d.inputMapping).length > 0);

const AgentNodeView: React.FC<NodeProps<AgentNodeData>> = ({ data, selected }) => {
  const status = data.status;
  const ring =
    status === "idle" ? (selected ? data.color : "#E2E8F0")
      : status === "running" ? "#F59E0B"
      : status === "success" ? "#10B981"
      : "#EF4444";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{
        opacity: 1,
        scale: status === "running" ? 1.04 : 1,
        boxShadow:
          status === "running" ? "0 0 0 4px rgba(245,158,11,0.30)"
          : status === "success" ? "0 0 0 3px rgba(16,185,129,0.28)"
          : status === "error" ? "0 0 0 3px rgba(239,68,68,0.28)"
          : "0 2px 10px rgba(0,0,0,0.08)",
      }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
      style={{
        width: 196, borderRadius: 12, background: "#fff",
        border: `1.5px solid ${ring}`,
      }}
    >
      <Handle type="target" position={Position.Left}
        style={{ background: data.color, width: 10, height: 10, border: "2px solid #fff" }} />
      <div style={{ padding: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: data.color, fontSize: 18 }}>{data.icon}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 12, lineHeight: 1.3, color: "#1E293B" }}>
              {data.label}
            </div>
          </div>
          <StatusBadge status={status} />
        </div>
        <div style={{ fontSize: 10, color: "#64748B", marginTop: 4, lineHeight: 1.4 }}>
          {data.description}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
          <span style={{ fontSize: 9, color: "#94A3B8", fontFamily: "monospace" }}>
            {data.agentType}
          </span>
          {hasConfig(data) && (
            <Tooltip title="已配置输入/工具/槽位映射">
              <span style={{ color: "#6366F1", fontSize: 11 }}><SettingOutlined /></span>
            </Tooltip>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Right}
        style={{ background: data.color, width: 10, height: 10, border: "2px solid #fff" }} />
    </motion.div>
  );
};

const nodeTypes = { agent: AgentNodeView };

// 默认 8 节点 + 链式数据流连线
function buildDefaultGraph(): { nodes: AgentNode[]; edges: Edge[] } {
  const nodes: AgentNode[] = SEED_DOMAIN_IDS.map((a, i) => ({
    id: a.id,
    type: "agent",
    position: { x: 40 + (i % 4) * 250, y: 40 + Math.floor(i / 4) * 150 },
    data: {
      agentType: a.id, label: a.name, description: a.description,
      icon: React.createElement(a.icon), color: a.color, status: "idle",
      userInput: "", selectedTools: [], inputMapping: {},
    },
  }));
  const edges: Edge[] = [];
  for (let i = 0; i < SEED_DOMAIN_IDS.length - 1; i++) {
    const s = SEED_DOMAIN_IDS[i].id;
    const t = SEED_DOMAIN_IDS[i + 1].id;
    edges.push({
      id: `e_${s}_${t}`, source: s, target: t,
      animated: true, style: { stroke: PRIMARY, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: PRIMARY },
    });
  }
  return { nodes, edges };
}

// ─────────────────────────────────────────────────────────────────────────────
// 主页面（内层，使用 React Flow hooks）
// ─────────────────────────────────────────────────────────────────────────────

const WorkflowInner: React.FC = () => {
  const { message } = App.useApp();
  const { fitView } = useReactFlow();

  const initial = useMemo(() => buildDefaultGraph(), []);
  const [nodes, setNodes, onNodesChange] = useNodesState<AgentNodeData>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initial.edges);

  const [workflowName, setWorkflowName] = useState("默认 PM 多智能体工作流");
  const [executing, setExecuting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<LogEntry[]>([]);

  // 工作流库（多租户）
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [currentWfId, setCurrentWfId] = useState<string | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveDesc, setSaveDesc] = useState("");
  const [projectId, setProjectId] = useState<string | undefined>();
  const [projectOptions, setProjectOptions] = useState<{ value: string; label: string }[]>([]);
  const [loadingLib, setLoadingLib] = useState(false);

  // ── 统一注册中心（全量 Agent：领域 + PMBOK）──
  const [registry, setRegistry] = useState<RegistryAgentItem[]>([]);
  const [regLoading, setRegLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<"all" | "domain" | "pmbok">("all");
  const [catFilter, setCatFilter] = useState<string>("all");
  const [kaFilter, setKaFilter] = useState<string>("all"); // 知识领域（仅 v6）

  // ── 节点配置抽屉 ──
  const [configNode, setConfigNode] = useState<AgentNode | null>(null);
  const [slotInfo, setSlotInfo] = useState<{ inputs: SlotItem[]; tools: SlotItem[]; outputs: SlotItem[] }>({ inputs: [], tools: [], outputs: [] });
  const [cfgUserInput, setCfgUserInput] = useState("");
  const [cfgTools, setCfgTools] = useState<string[]>([]);
  const [cfgMapping, setCfgMapping] = useState<Record<string, string>>({});
  const [slotLoading, setSlotLoading] = useState(false);

  // ── 运行历史 ──
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDetail, setHistoryDetail] = useState<any | null>(null);

  // ── 最近一次运行结果（用于节点抽屉展示输出）──
  const [lastRun, setLastRun] = useState<any | null>(null);

  const addLog = useCallback((label: string, msg: string, level: LogEntry["level"]) => {
    setLog(prev => [...prev, {
      id: uid("log"), time: new Date().toLocaleTimeString(),
      label, message: msg, level,
    }]);
  }, []);

  // 加载统一注册中心
  useEffect(() => {
    (async () => {
      try {
        const r: any = await agentApi.registry();
        setRegistry(r?.items || []);
      } catch (e: any) {
        message.error(e?.response?.data?.detail || "加载 Agent 注册中心失败");
      } finally {
        setRegLoading(false);
      }
    })();
  }, [message]);

  // 体系分类（去重，保持稳定顺序）
  const categories = useMemo(() => {
    const order = ["领域分析", "PMBOK第6版·49过程", "PMBOK第8版·原则", "PMBOK第8版·绩效域", "PMBOK第8版·裁剪", "CPMAI·AI项目管理阶段", "CPMAI·可信AI框架"];
    const present = new Set(registry.map(a => a.category));
    return ["all", ...order.filter(c => present.has(c))];
  }, [registry]);

  // v6 知识领域子筛选
  const knowledgeAreas = useMemo(() => {
    if (catFilter !== "PMBOK第6版·49过程") return [];
    const set = new Set<string>();
    registry.forEach(a => { if (a.category === "PMBOK第6版·49过程" && a.extra?.knowledge_area) set.add(a.extra.knowledge_area); });
    return Array.from(set);
  }, [registry, catFilter]);

  // 工具箱过滤后的 Agent 列表
  const toolbox = useMemo(() => {
    const kw = search.trim().toLowerCase();
    return registry.filter(a => {
      if (sourceFilter !== "all" && a.source !== sourceFilter) return false;
      if (catFilter !== "all" && a.category !== catFilter) return false;
      if (catFilter === "PMBOK第6版·49过程" && kaFilter !== "all" && a.extra?.knowledge_area !== kaFilter) return false;
      if (kw) {
        const hay = `${a.id} ${a.name} ${a.name_en} ${a.description} ${(a.tags || []).join(" ")}`.toLowerCase();
        if (!hay.includes(kw)) return false;
      }
      return true;
    });
  }, [registry, sourceFilter, catFilter, kaFilter, search]);

  // 解析图标 / 配色
  const resolveMeta = useCallback((a: RegistryAgentItem) => {
    const icon = CAT_ICON[a.category] || ICON_MAP[a.icon] || RobotOutlined;
    const color = a.color || CAT_COLOR[a.category] || PRIMARY;
    return { icon, color };
  }, []);

  // ── 从工具箱点击新增节点 ──
  const addAgentNode = useCallback((a: RegistryAgentItem) => {
    const { icon, color } = resolveMeta(a);
    const id = uid(`n_${a.id}`);
    const cols = 4;
    const idx = nodes.length;
    const position = { x: 40 + (idx % cols) * 250, y: 40 + Math.floor(idx / cols) * 150 };
    const newNode: AgentNode = {
      id, type: "agent", position,
      data: {
        agentType: a.id, label: a.name, description: a.description || a.category,
        icon: React.createElement(icon), color, status: "idle",
        userInput: "", selectedTools: [], inputMapping: {},
      },
    };
    setNodes(nds => [...nds, newNode]);
    message.success(`已添加「${a.name}」节点`);
  }, [nodes.length, setNodes, message, resolveMeta]);

  // ── 连线（边 = depends_on；支持扇入/扇出）──
  const onConnect = useCallback((connection: Connection) => {
    setEdges(eds => addEdge({
      ...connection, animated: true,
      style: { stroke: PRIMARY, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: PRIMARY },
    }, eds));
  }, [setEdges]);

  // ── 清空 ──
  const handleClear = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setLog([]);
    setProgress(0);
    setLastRun(null);
    message.info("画布已清空");
  }, [setNodes, setEdges, message]);

  // ── 自动布局：按 DAG 分层（从左到右）──
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;
    const adj = new Map<string, string[]>();
    edges.forEach(e => { if (!adj.has(e.source)) adj.set(e.source, []); adj.get(e.source)!.push(e.target); });
    const layer = new Map<string, number>();
    const calc = (id: string, stack: Set<string>): number => {
      if (layer.has(id)) return layer.get(id)!;
      if (stack.has(id)) return 0;
      stack.add(id);
      let l = 0;
      for (const t of adj.get(id) || []) l = Math.max(l, calc(t, stack) + 1);
      stack.delete(id);
      layer.set(id, l);
      return l;
    };
    nodes.forEach(n => calc(n.id, new Set()));
    const byLayer: Record<number, string[]> = {};
    nodes.forEach(n => { const l = layer.get(n.id) || 0; (byLayer[l] = byLayer[l] || []).push(n.id); });
    const pos: Record<string, { x: number; y: number }> = {};
    Object.keys(byLayer).forEach(k => {
      const l = Number(k);
      byLayer[l].forEach((id, i) => { pos[id] = { x: 60 + l * 270, y: 60 + i * 150 }; });
    });
    setNodes(nds => nds.map(n => ({ ...n, position: pos[n.id] || n.position })));
    setTimeout(() => fitView({ padding: 0.2 }), 60);
  }, [nodes, edges, setNodes, fitView]);

  // ── 由节点/边构建后端步骤（node.id 作为 DAG 标签，保证唯一）──
  const buildSteps = useCallback((): any[] => {
    return nodes.map(n => ({
      agent_type: n.data.agentType,
      label: n.id,
      depends_on: edges.filter(e => e.target === n.id).map(e => e.source),
      user_input: n.data.userInput || "",
      selected_tools: n.data.selectedTools || [],
      input_mapping: n.data.inputMapping || {},
    }));
  }, [nodes, edges]);

  // ── 运行工作流（异步调度：提交后立即拿 run_id，轮询实时进度）──
  const handleRun = useCallback(async () => {
    if (nodes.length === 0) { message.warning("请先添加工作流节点"); return; }
    setExecuting(true);
    setProgress(0);
    setLog([]);
    setLastRun(null);
    setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, status: "idle" } })));

    const steps = buildSteps();
    const nodeLabelById = new Map(nodes.map(n => [n.id, n.data.label]));
    addLog("工作流", `提交执行，共 ${steps.length} 个节点（异步 DAG 调度）`, "info");

    let runId: string | undefined;
    try {
      const res: any = await workflowApi.execute({ steps, project_id: projectId });
      runId = res?.run_id;
      if (!runId) throw new Error("后端未返回 run_id");
      addLog("工作流", `已提交，run_id=${runId.slice(0, 8)}…`, "info");
    } catch (e: any) {
      addLog("工作流", `提交失败: ${e?.response?.data?.detail || e?.message}`, "error");
      message.error("提交执行失败");
      setExecuting(false);
      return;
    }

    // 轮询实时状态
    const seen = new Set<string>();
    const total = steps.length;
    let failed = 0;
    try {
      while (true) {
        let st: any;
        try {
          st = await workflowApi.getRunStatus(runId!);
        } catch (e: any) {
          if ((e as any)?.response?.status === 404) { addLog("工作流", "运行记录已过期（持久化文件可能已被清理）", "error"); break; }
          await sleep(1500); continue;
        }
        const results = st?.results || {};
        for (const [label, r] of Object.entries(results)) {
          const rr = r as any;
          const disp = nodeLabelById.get(label) || label;
          let st2: NodeStatus = "idle";
          if (rr.status === "running") st2 = "running";
          else if (rr.status === "completed") st2 = "success";
          else if (rr.status === "failed") st2 = "error";
          setNodes(nds => nds.map(n => n.id === label ? { ...n, data: { ...n.data, status: st2 } } : n));

          if ((rr.status === "completed" || rr.status === "failed") && !seen.has(label)) {
            seen.add(label);
            if (rr.status === "failed") { failed++; addLog(disp, `失败: ${rr.error || "未知错误"}`, "error"); }
            else addLog(disp, "执行完成", "success");
            const out = rr.output_preview as string | undefined;
            if (out) addLog(disp, `输出摘要: ${out.slice(0, 160)}${out.length > 160 ? "…" : ""}`, "info");
          }
        }
        const finished = Object.values(results).filter((r: any) => r.status === "completed" || r.status === "failed").length;
        setProgress(Math.round((finished / total) * 100));

        const status = st?.status;
        if (status === "completed" || status === "partial_failure" || status === "failed") {
          setLastRun(st);
          break;
        }
        await sleep(1500);
      }
      const finalSt: any = await workflowApi.getRunStatus(runId!).catch(() => lastRun);
      const fstatus = finalSt?.status || "unknown";
      addLog("工作流", `执行结束，状态: ${fstatus}${failed ? `，失败 ${failed} 步` : ""}`, failed ? "error" : "success");
      message.success(`工作流执行完成（状态：${fstatus}）`);
      setTimeout(() => fitView({ padding: 0.2 }), 60);
    } catch (e: any) {
      addLog("工作流", `轮询异常: ${e?.message || "超时"}`, "error");
      message.error("运行查询失败");
    } finally {
      setExecuting(false);
    }
  }, [nodes, edges, setNodes, message, addLog, fitView, projectId, buildSteps, lastRun]);

  // ── 删除选中的边/节点 ──
  const removeSelected = useCallback(() => {
    setNodes(nds => nds.filter(n => !n.selected));
    setEdges(eds => eds.filter(e => !e.selected));
  }, [setNodes, setEdges]);

  // ── 工作流库加载 ──
  const loadLibrary = useCallback(async () => {
    setLoadingLib(true);
    try {
      const [wfRes, projRes] = await Promise.all([
        workflowApi.list({}).catch(() => ({ items: [] })),
        projectApi.list({ page: 1, size: 300 }).catch(() => ({ items: [] })),
      ]);
      setWorkflows((wfRes.items || []));
      setProjectOptions((projRes.items || []).map((p: any) => ({ value: p.id, label: p.name })));
    } catch (e: any) {
      message.error(e?.message || "加载工作流库失败");
    } finally {
      setLoadingLib(false);
    }
  }, [message]);

  useEffect(() => { loadLibrary(); }, [loadLibrary]);

  const handleSave = useCallback(async () => {
    if (!workflowName.trim()) { message.warning("请输入工作流名称"); return; }
    const steps = buildSteps();
    const payload = { name: workflowName, description: saveDesc, project_id: projectId, steps };
    try {
      if (currentWfId) {
        await workflowApi.update(currentWfId, payload);
        message.success("工作流已更新");
      } else {
        const res: any = await workflowApi.create(payload);
        setCurrentWfId(res?.workflow?.id || res?.id || null);
        message.success("工作流已保存");
      }
      setSaveOpen(false);
      loadLibrary();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || "保存失败");
    }
  }, [workflowName, saveDesc, projectId, currentWfId, message, loadLibrary, buildSteps]);

  // ── 载入已保存工作流（重映射旧 label → 新节点 id）──
  const loadWorkflow = useCallback(async (id: string) => {
    try {
      const res: any = await workflowApi.get(id);
      const wf = res?.workflow || res;
      const steps: any[] = wf.steps || [];
      const oldToNew = new Map<string, string>();
      const newNodes: AgentNode[] = steps.map((s: any, i: number) => {
        const a = registry.find(r => r.id === s.agent_type) || SEED_DOMAIN_IDS.find(d => d.id === s.agent_type);
        const meta = a ? resolveMeta(a as RegistryAgentItem) : { icon: RobotOutlined, color: PRIMARY };
        const nid = uid(`n_${s.agent_type || i}`);
        oldToNew.set(s.label, nid);
        oldToNew.set(s.agent_type, nid);
        return {
          id: nid, type: "agent",
          position: { x: 40 + (i % 4) * 250, y: 40 + Math.floor(i / 4) * 150 },
          data: {
            agentType: s.agent_type, label: s.label || (a as any)?.name || s.agent_type,
            description: (a as any)?.description || s.agent_type,
            icon: React.createElement(meta.icon), color: meta.color, status: "idle",
            userInput: s.user_input || "", selectedTools: s.selected_tools || [],
            inputMapping: s.input_mapping || {},
          },
        };
      });
      // 重映射 input_mapping 的旧 label 值 → 新节点 id
      newNodes.forEach(n => {
        const m = n.data.inputMapping || {};
        const nm: Record<string, string> = {};
        Object.entries(m).forEach(([k, v]) => { nm[k] = oldToNew.get(v) || v; });
        n.data.inputMapping = nm;
      });
      const newEdges: Edge[] = [];
      steps.forEach((s: any) => {
        const tid = oldToNew.get(s.label) || oldToNew.get(s.agent_type);
        (s.depends_on || []).forEach((d: string) => {
          const sid = oldToNew.get(d);
          if (sid && tid && sid !== tid) {
            newEdges.push({
              id: uid("e"), source: sid, target: tid,
              animated: true, style: { stroke: PRIMARY, strokeWidth: 2 },
              markerEnd: { type: MarkerType.ArrowClosed, color: PRIMARY },
            });
          }
        });
      });
      setNodes(newNodes);
      setEdges(newEdges);
      setWorkflowName(wf.name || workflowName);
      setSaveDesc(wf.description || "");
      setCurrentWfId(wf.id || id);
      setLastRun(null);
      message.success(`已载入「${wf.name || ""}」`);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || "载入失败");
    }
  }, [setNodes, setEdges, message, workflowName, registry, resolveMeta]);

  const handleDeleteWf = useCallback(async (id: string) => {
    try {
      await workflowApi.remove(id);
      if (currentWfId === id) setCurrentWfId(null);
      message.success("已删除");
      loadLibrary();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || "删除失败");
    }
  }, [currentWfId, message, loadLibrary]);

  // ── 节点配置抽屉：打开时拉取结构化 ITTO 槽位 ──
  useEffect(() => {
    if (!configNode) { setSlotInfo({ inputs: [], tools: [], outputs: [] }); return; }
    setCfgUserInput(configNode.data.userInput || "");
    setCfgTools(configNode.data.selectedTools || []);
    setCfgMapping(configNode.data.inputMapping || {});
    let cancelled = false;
    setSlotLoading(true);
    (async () => {
      try {
        const r: any = await agentApi.prepare(configNode.data.agentType, projectId ? { project_id: projectId } : {});
        if (!cancelled) {
          const norm = (arr: any[] = []): SlotItem[] =>
            (arr || []).filter((it: any) => it && it.enabled !== false)
              .map((it: any) => ({ key: it.key, label: it.label || it.key, optional: !!it.optional, enabled: it.enabled !== false, kind: it.kind || "file" }));
          setSlotInfo({ inputs: norm(r?.inputs), tools: norm(r?.tools), outputs: norm(r?.outputs) });
        }
      } catch {
        if (!cancelled) setSlotInfo({ inputs: [], tools: [], outputs: [] });
      } finally {
        if (!cancelled) setSlotLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [configNode, projectId]);

  // 当前节点在最近一次运行中的结果
  const currentNodeRun = useMemo(() => {
    if (!configNode || !lastRun?.results) return null;
    return (lastRun.results as any)[configNode.id] || null;
  }, [configNode, lastRun]);

  const upstreamOptions = useMemo(() => {
    if (!configNode) return [];
    return nodes
      .filter(n => edges.some(e => e.target === configNode.id && e.source === n.id))
      .map(n => ({ value: n.id, label: n.data.label }));
  }, [configNode, nodes, edges]);

  // ── 运行历史 ──
  const openHistory = useCallback(async () => {
    if (!currentWfId) { message.warning("请先保存工作流以查看运行历史"); return; }
    setHistoryOpen(true);
    setHistoryDetail(null);
    setHistoryLoading(true);
    try {
      const r: any = await workflowApi.getRuns(currentWfId);
      setHistoryList(r?.items || []);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || e?.message || "加载历史失败");
    } finally {
      setHistoryLoading(false);
    }
  }, [currentWfId, message]);

  // ── 渲染 ──
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)" }}>
      {/* Header：工作流名称 + 操作 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ApartmentOutlined style={{ color: PRIMARY, fontSize: 22 }} />
          <div>
            <Input
              value={workflowName}
              onChange={e => setWorkflowName(e.target.value)}
              variant="borderless"
              style={{ fontSize: 18, fontWeight: 600, padding: 0, height: 28, width: 320 }}
              placeholder="工作流名称"
            />
            <div style={{ fontSize: 12, color: "#64748B" }}>
              {nodes.length} 个 Agent 节点 · {edges.length} 条数据流连线
              {currentWfId && <Tag color="blue" style={{ marginLeft: 6 }}>已保存</Tag>}
            </div>
          </div>
        </div>
        <Space>
          <Select
            style={{ width: 180 }} placeholder="绑定项目（可选）" allowClear
            value={projectId} onChange={setProjectId} options={projectOptions}
          />
          <Button icon={<HistoryOutlined />} onClick={openHistory} disabled={!currentWfId}>
            运行历史
          </Button>
          <Button icon={<SaveOutlined />} onClick={() => setSaveOpen(true)} disabled={nodes.length === 0}>
            {currentWfId ? "更新" : "保存"}
          </Button>
        </Space>
      </div>

      {/* 三栏布局 */}
      <div style={{ display: "flex", flex: 1, gap: 12, overflow: "hidden" }}>
        {/* 左栏：Agent 工具箱（统一注册中心）+ 工作流库 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, width: 260, flexShrink: 0, overflow: "hidden" }}>
          <Card
            size="small" title={<Space><PlusOutlined /><span>Agent 工具箱</span></Space>}
            data-tour="workflow-add"
            style={{ borderRadius: 12, overflow: "hidden", flexShrink: 0, display: "flex", flexDirection: "column", maxHeight: "64%" }}
            bodyStyle={{ padding: 10, overflow: "hidden", display: "flex", flexDirection: "column" }}
          >
            <Input
              prefix={<SearchOutlined />} allowClear placeholder="搜索 Agent / 过程 id"
              value={search} onChange={e => setSearch(e.target.value)} size="small" style={{ marginBottom: 8 }}
            />
            <Segmented
              size="small" block style={{ marginBottom: 8 }}
              value={sourceFilter}
              onChange={(v) => { setSourceFilter(v as any); setCatFilter("all"); setKaFilter("all"); }}
              options={[
                { label: "全部", value: "all" },
                { label: "领域", value: "domain" },
                { label: "PMBOK", value: "pmbok" },
              ]}
            />
            <Select
              size="small" style={{ marginBottom: 8 }} value={catFilter} onChange={(v) => { setCatFilter(v); setKaFilter("all"); }}
              options={categories.map(c => ({ value: c, label: c === "all" ? "全部体系" : c }))}
            />
            {catFilter === "PMBOK第6版·49过程" && knowledgeAreas.length > 0 && (
              <Select
                size="small" style={{ marginBottom: 8 }} value={kaFilter} onChange={setKaFilter}
                options={[{ value: "all", label: "全部知识领域" }, ...knowledgeAreas.map(k => ({ value: k, label: k }))]}
              />
            )}
            <div style={{ fontSize: 11, color: "#94A3B8", marginBottom: 6 }}>点击添加节点（{toolbox.length}）</div>
            <div style={{ overflow: "auto", flex: 1 }}>
              {regLoading && <div style={{ textAlign: "center", padding: 16 }}><Spin /></div>}
              {!regLoading && toolbox.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无匹配 Agent" />}
              {toolbox.map(a => {
                const { icon, color } = resolveMeta(a);
                const IconC = icon;
                return (
                  <div key={a.id} onClick={() => addAgentNode(a)} style={{ cursor: "grab", marginBottom: 6 }}>
                    <Card size="small" hoverable bodyStyle={{ padding: "6px 8px" }}
                      style={{ borderLeft: `3px solid ${color}`, borderRadius: 8 }}>
                      <Space size={6}>
                        <span style={{ color, fontSize: 15 }}><IconC /></span>
                        <div style={{ minWidth: 0 }}>
                          <Text style={{ fontSize: 12, fontWeight: 600, display: "block", lineHeight: 1.3 }}>
                            {a.name}
                            <Tag color={color} style={{ marginLeft: 4, fontSize: 9, padding: "0 4px", lineHeight: "14px" }}>{a.id}</Tag>
                          </Text>
                          <Text type="secondary" style={{ fontSize: 10, display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {a.description || a.category}
                          </Text>
                        </div>
                      </Space>
                    </Card>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card
            size="small" title={<Space><FolderOpenOutlined /><span>工作流库</span></Space>}
            style={{ borderRadius: 12, overflow: "auto", flex: 1 }}
            bodyStyle={{ padding: 8 }}
            extra={<Button size="small" type="text" icon={<ReloadOutlined />} loading={loadingLib} onClick={loadLibrary} />}
          >
            {loadingLib && workflows.length === 0 && (
              <div style={{ textAlign: "center", padding: 16, color: "#94A3B8" }}><LoadingOutlined /> 加载中…</div>
            )}
            {!loadingLib && workflows.length === 0 && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无工作流" style={{ margin: "12px 0" }} />
            )}
            <List
              size="small" dataSource={workflows}
              renderItem={(w: any) => (
                <List.Item
                  actions={[
                    <Button key="load" type="link" size="small" icon={<FolderOpenOutlined />} onClick={() => loadWorkflow(w.id)}>载入</Button>,
                    <Popconfirm key="del" title="确认删除该工作流？" onConfirm={() => handleDeleteWf(w.id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    title={<Text style={{ fontSize: 12 }}>{w.name}</Text>}
                    description={<Text type="secondary" style={{ fontSize: 10 }}>{(w.steps || []).length} 步</Text>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </div>

        {/* 中栏：工具栏 + 画布 */}
        <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center", flexWrap: "wrap" }}>
            <Button type="primary" icon={<PlayCircleOutlined />} loading={executing} onClick={handleRun} data-tour="workflow-run">
              运行工作流
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleAutoLayout} disabled={nodes.length === 0}>
              自动布局
            </Button>
            <Button icon={<ClearOutlined />} onClick={handleClear} disabled={nodes.length === 0}>
              清空
            </Button>
            <Button icon={<DeleteOutlined />} onClick={removeSelected} disabled={nodes.length === 0}>
              删除选中
            </Button>
            <div style={{ flex: 1 }} />
            <Progress
              percent={progress} size="small" style={{ width: 160 }}
              strokeColor={PRIMARY} status={executing ? "active" : "normal"}
            />
          </div>

          <Card
            size="small" style={{ flex: 1, borderRadius: 12, overflow: "hidden", minHeight: 360 }}
            bodyStyle={{ padding: 0, height: "100%" }}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              onNodeClick={(_, node) => setConfigNode(node as AgentNode)}
              fitView
              proOptions={{ hideAttribution: true }}
              deleteKeyCode={["Backspace", "Delete"]}
            >
              <Background color="#E2E8F0" gap={16} />
              <Controls />
              <MiniMap
                nodeColor={(n: any) => (n.data?.color as string) || PRIMARY}
                maskColor="rgba(241,245,249,0.6)"
                style={{ borderRadius: 8 }}
              />
            </ReactFlow>
          </Card>
        </div>

        {/* 右栏：执行日志 / 进度 */}
        <Card
          size="small" title={<Space><CheckCircleOutlined /><span>执行日志 / 进度</span></Space>}
          style={{ width: 280, flexShrink: 0, borderRadius: 12, overflow: "auto" }}
          bodyStyle={{ padding: 10 }}
        >
          <Text style={{ fontSize: 11, fontWeight: 600, color: "#6B7280" }}>节点状态</Text>
          <div style={{ marginTop: 6 }}>
            {nodes.length === 0 && <Text type="secondary" style={{ fontSize: 11 }}>暂无节点</Text>}
            {nodes.map(n => {
              const m = STATUS_META[n.data.status];
              const run = lastRun?.results?.[n.id];
              return (
                <div key={n.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ color: n.data.color, fontSize: 14 }}>{n.data.icon}</span>
                  <Text style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {n.data.label}
                  </Text>
                  {run?.output_preview && (
                    <Tooltip title="查看输出摘要">
                      <EyeOutlined style={{ color: "#6366F1", cursor: "pointer" }} onClick={() => setConfigNode(n)} />
                    </Tooltip>
                  )}
                  <span style={{ color: m.color, fontSize: 11, fontWeight: 600 }}>{m.text}</span>
                </div>
              );
            })}
          </div>

          <div style={{ height: 1, background: "#E2E8F0", margin: "10px 0" }} />

          <Text style={{ fontSize: 11, fontWeight: 600, color: "#6B7280" }}>运行日志</Text>
          <div style={{ marginTop: 6, maxHeight: 260, overflow: "auto" }}>
            {log.length === 0 && <Text type="secondary" style={{ fontSize: 11 }}>运行后此处显示实时日志</Text>}
            {log.map(l => (
              <div key={l.id} style={{ marginBottom: 6, fontSize: 11 }}>
                <span style={{ color: "#94A3B8" }}>{l.time}</span>{" "}
                <span style={{ color: l.level === "success" ? "#10B981" : l.level === "error" ? "#EF4444" : "#1E293B", fontWeight: 600 }}>
                  {l.label}
                </span>
                <div style={{ color: "#64748B" }}>{l.message}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, fontSize: 10, color: "#94A3B8" }}>
            <SwapOutlined /> 连线即「依赖」：一个节点可连多个上游（扇入合并），也可被多个下游引用（扇出复用）。
          </div>
        </Card>
      </div>

      {/* 节点配置抽屉 */}
      <Drawer
        title={configNode ? (
          <Space>
            <span style={{ color: configNode.data.color }}>{configNode.data.icon}</span>
            <span>{configNode.data.label}</span>
            <Tag color={configNode.data.color}>{configNode.data.agentType}</Tag>
          </Space>
        ) : "节点配置"}
        width={420}
        open={!!configNode}
        onClose={() => setConfigNode(null)}
        extra={<Button type="primary" onClick={() => {
          if (!configNode) return;
          const id = configNode.id;
          setNodes(nds => nds.map(n => n.id === id ? {
            ...n, data: { ...n.data, userInput: cfgUserInput, selectedTools: cfgTools, inputMapping: cfgMapping },
          } : n));
          message.success("节点配置已保存");
          setConfigNode(null);
        }}>保存配置</Button>}
      >
        {configNode && (
          <div>
            <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>补充输入（内联文本）</Text>
            <Input.TextArea
              rows={3} value={cfgUserInput} onChange={e => setCfgUserInput(e.target.value)}
              placeholder="可选：作为该 Agent 的内联补充输入，与上游输出拼接后一起喂入"
            />

            <div style={{ height: 12 }} />
            <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>
              工具技术（selected_tools）
            </Text>
            {slotLoading ? <Spin /> : (
              slotInfo.tools.length === 0
                ? <Text type="secondary" style={{ fontSize: 11 }}>该 Agent 无可选工具技术</Text>
                : <Select
                    mode="multiple" allowClear style={{ width: "100%" }}
                    value={cfgTools} onChange={setCfgTools}
                    options={slotInfo.tools.map(t => ({ value: t.key, label: `${t.label}${t.optional ? "（可选）" : ""}` }))}
                    placeholder="勾选工具技术（空=全部）"
                  />
            )}

            <div style={{ height: 12 }} />
            <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>
              输入槽位映射（input_mapping）
            </Text>
            {slotLoading ? <Spin /> : (
              <div>
                {upstreamOptions.length === 0 && (
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    该节点暂无上游（未连线）。不映射时，运行时将自动合并全部上游输出；无上游则仅用内联输入。
                  </Text>
                )}
                {upstreamOptions.length > 0 && slotInfo.inputs.length === 0 && (
                  <Text type="secondary" style={{ fontSize: 11 }}>该 Agent 无结构化输入槽位，无需映射（自动合并全部上游输出）。</Text>
                )}
                {slotInfo.inputs.map(slot => (
                  <div key={slot.key} style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: "#475569", marginBottom: 2 }}>
                      {slot.label}{slot.optional ? "（可选）" : <Text type="danger" style={{ fontSize: 11 }}>（必填）</Text>}
                    </div>
                    <Select
                      size="small" style={{ width: "100%" }} allowClear
                      value={cfgMapping[slot.key] || undefined}
                      onChange={(v) => setCfgMapping(prev => {
                        const next = { ...prev };
                        if (v) next[slot.key] = v; else delete next[slot.key];
                        return next;
                      })}
                      options={upstreamOptions.map(o => ({ value: o.value, label: `绑定上游：${o.label}` }))}
                      placeholder="不绑定（默认：自动合并全部上游输出）"
                    />
                  </div>
                ))}
              </div>
            )}

            <div style={{ height: 12 }} />
            <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>输出槽位</Text>
            {slotLoading ? <Spin /> : (
              slotInfo.outputs.length === 0
                ? <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
                : <div>{slotInfo.outputs.map(o => <Tag key={o.key} color="green" style={{ marginBottom: 4 }}>{o.label}</Tag>)}</div>
            )}

            {currentNodeRun?.output_preview && (
              <>
                <div style={{ height: 12 }} />
                <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>最近运行输出（摘要）</Text>
                <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 8, padding: 10, fontSize: 11, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap", color: "#334155" }}>
                  {currentNodeRun.output_preview}
                </div>
              </>
            )}
          </div>
        )}
      </Drawer>

      {/* 运行历史抽屉 */}
      <Drawer
        title="运行历史" width={460} open={historyOpen}
        onClose={() => { setHistoryOpen(false); setHistoryDetail(null); }}
      >
        {historyLoading ? <div style={{ textAlign: "center", padding: 24 }}><Spin /></div> : (
          historyDetail ? (
            <div>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => setHistoryDetail(null)} style={{ marginBottom: 8 }}>
                返回列表
              </Button>
              <div style={{ fontSize: 12, marginBottom: 8 }}>
                状态：<Tag color={historyDetail.status === "completed" ? "green" : historyDetail.status === "failed" ? "red" : "orange"}>{historyDetail.status}</Tag>
                {" "}创建：{historyDetail.created_at}
              </div>
              {Object.entries(historyDetail.results || {}).map(([label, r]: any) => (
                <Card key={label} size="small" style={{ marginBottom: 8, borderRadius: 8 }}>
                  <div style={{ fontWeight: 600, fontSize: 12 }}>{nodes.find(n => n.id === label)?.data.label || label}</div>
                  <Tag color={r.status === "completed" ? "green" : r.status === "failed" ? "red" : "default"} style={{ marginTop: 4 }}>
                    {r.status}
                  </Tag>
                  {r.output_preview && (
                    <div style={{ marginTop: 6, fontSize: 11, background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: 6, padding: 8, maxHeight: 160, overflow: "auto", whiteSpace: "pre-wrap", color: "#334155" }}>
                      {r.output_preview}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          ) : (
            <List
              dataSource={historyList}
              locale={{ emptyText: <Empty description="暂无运行历史" /> }}
              renderItem={(h: any) => (
                <List.Item
                  actions={[<Button key="v" type="link" size="small" onClick={() => setHistoryDetail(h)}>查看</Button>]}
                >
                  <List.Item.Meta
                    title={<Space>
                      <Tag color={h.status === "completed" ? "green" : h.status === "failed" ? "red" : "orange"}>{h.status}</Tag>
                      <span style={{ fontSize: 12 }}>{h.run_id?.slice(0, 8)}</span>
                    </Space>}
                    description={<Text type="secondary" style={{ fontSize: 10 }}>{h.created_at} · {(h.steps || []).length} 步</Text>}
                  />
                </List.Item>
              )}
            />
          )
        )}
      </Drawer>

      <Modal
        title={currentWfId ? "更新工作流" : "保存工作流"}
        open={saveOpen} onOk={handleSave} onCancel={() => setSaveOpen(false)}
        okText={currentWfId ? "更新" : "保存"} cancelText="取消"
      >
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>名称 *</Text>
          <Input value={workflowName} onChange={e => setWorkflowName(e.target.value)} placeholder="例如：项目健康检查" />
        </div>
        <div style={{ marginBottom: 12 }}>
          <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>描述</Text>
          <Input.TextArea rows={3} value={saveDesc} onChange={e => setSaveDesc(e.target.value)} placeholder="描述工作流用途…" />
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {currentWfId ? "将更新当前工作流" : `将保存 ${nodes.length} 个节点的工作流定义`}
          </Text>
        </div>
      </Modal>
    </div>
  );
};

const AgentWorkflow: React.FC = () => (
  <ReactFlowProvider>
    <WorkflowInner />
  </ReactFlowProvider>
);

export default AgentWorkflow;
