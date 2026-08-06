import React, { useEffect, useMemo, useState } from "react";
import {
  Card, Typography, Tabs, Tag, Button, Select, Space, App, Drawer,
  Spin, Alert, List, Input, Form, Modal,
  Row, Col, Tooltip, Badge, Divider, Switch,
} from "antd";
import {
  BookOutlined, PlayCircleOutlined, ProjectOutlined, ExperimentOutlined,
  PartitionOutlined, NodeIndexOutlined, SafetyOutlined, ApartmentOutlined,
  CompassOutlined, RobotOutlined, EditOutlined,
  DeleteOutlined, SaveOutlined, ThunderboltOutlined, CheckOutlined,
  CodeOutlined, ToolOutlined, CloudDownloadOutlined, PlusOutlined,
} from "@ant-design/icons";
import { pmbokApi } from "../api";
import { agentApi, projectApi } from "../api";
import { useNavigate } from "react-router-dom";
import AgentRunDialog from "../components/AgentRunDialog";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface PmbokProcess {
  id: string;
  name_cn: string;
  name_en: string;
  kind: string;
  category: string;
  process_group: string;
  knowledge_area: string;
  summary: string;
  inputs: string[];
  tools: string[];
  outputs: string[];
  v8: string;
}
interface CategoryBlock {
  category: string;
  count: number;
  items: PmbokProcess[];
}

interface AnyAgent {
  id: string;
  name: string;
  name_en?: string;
  description?: string;
  category?: string;
  type?: string;
  icon?: string;
  color?: string;
  inputHint?: string;
  tags?: string[];
  accuracy?: number;
}

// 结构化 ITTO 单项（后端 get_structured_itto 返回）
interface IttoItem {
  key: string;
  label: string;
  optional?: boolean;
  kind?: string;
  template_prompt?: string;
  enabled?: boolean; // 仅工具技术：是否被勾选使用
}
interface PrepareInput extends IttoItem {
  exists: boolean;
  ref?: string | null;
  title?: string | null;
  source?: string | null;
}
interface PrepareResult {
  agent_id: string;
  project_id?: string | null;
  has_project: boolean;
  inputs: PrepareInput[];
  missing_required: string[];
  tools: IttoItem[];
  outputs: IttoItem[];
}

// ============ 结构化 ITTO 条目编辑辅助 ============
// 每一项都有独立「选用」开关（enabled，默认 true）；输入项另有「可选/必需」语义开关（optional）。
const patchItto = (
  setter: React.Dispatch<React.SetStateAction<IttoItem[]>>,
  key: string,
  patch: Partial<IttoItem>,
) => setter((arr) => arr.map((x) => (x.key === key ? { ...x, ...patch } : x)));

const addItto = (
  setter: React.Dispatch<React.SetStateAction<IttoItem[]>>,
  kind: "input" | "tool" | "output",
) =>
  setter((arr) => [
    ...arr,
    {
      key: `${kind}_${Date.now().toString(36)}_${Math.floor(Math.random() * 1e4).toString(36)}`,
      label: "新条目",
      enabled: true,
      ...(kind === "input" ? { optional: false } : {}),
    },
  ]);

const removeItto = (
  setter: React.Dispatch<React.SetStateAction<IttoItem[]>>,
  key: string,
) => setter((arr) => arr.filter((x) => x.key !== key));

// 六大体系配色与图标
const CAT_STYLE: Record<string, { color: string; icon: React.ReactNode }> = {
  "PMBOK第6版·49过程": { color: "#4F46E5", icon: <PartitionOutlined /> },
  "PMBOK第8版·原则": { color: "#10B981", icon: <CompassOutlined /> },
  "PMBOK第8版·绩效域": { color: "#6366F1", icon: <ApartmentOutlined /> },
  "PMBOK第8版·裁剪": { color: "#06B6D4", icon: <NodeIndexOutlined /> },
  "CPMAI·AI项目管理阶段": { color: "#F59E0B", icon: <RobotOutlined /> },
  "CPMAI·可信AI框架": { color: "#EF4444", icon: <SafetyOutlined /> },
};

const PmbokAgents: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  const [categories, setCategories] = useState<CategoryBlock[]>([]);
  const [activeTab, setActiveTab] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState<string | undefined>();
  const [activeAgents, setActiveAgents] = useState<AnyAgent[]>([]);

  // === Agent 深度编辑器 ===
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<AnyAgent | null>(null);
  const [editOverride, setEditOverride] = useState<any>(null);
  const [, setEditBase] = useState<any>(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editForm] = Form.useForm();

  // 结构化 ITTO 编辑态（每项可配 optional / enabled）
  const [ittoInputs, setIttoInputs] = useState<IttoItem[]>([]);
  const [ittoTools, setIttoTools] = useState<IttoItem[]>([]);
  const [ittoOutputs, setIttoOutputs] = useState<IttoItem[]>([]);

  // 统一手动运行对话框（检索 → 工具运用 → Markdown 结果；快慢模式自选）
  const [runDialogAgent, setRunDialogAgent] = useState<{ id: string; name: string; kind: "domain" | "pmbok" } | null>(null);
  const [runDialogOpen, setRunDialogOpen] = useState(false);

  // 草稿列表 / 草稿刷新触发
  const [, setDraftTick] = useState(0);

  // 浏览器下载由 AgentRunDialog 内部处理

  useEffect(() => {
    (async () => {
      try {
        const [cat, pj, agentState] = await Promise.all([
          pmbokApi.catalog(),
          projectApi.list({ page: 1, size: 200 }).catch(() => ({ items: [] })),
          agentApi.list().catch(() => ({ items: [] })),
        ]);
        // 优先使用后端分组结构
        let catBlocks: CategoryBlock[] = [];
        if (cat.grouped?.categories?.length) {
          catBlocks = cat.grouped.categories;
        } else {
          const m: Record<string, PmbokProcess[]> = {};
          for (const p of (cat.items || [])) (m[p.category] ||= []).push(p);
          catBlocks = Object.entries(m).map(([category, items]) => ({ category, count: items.length, items }));
        }
        setCategories(catBlocks);
        // 默认选中第一个分类
        if (catBlocks.length && !activeTab) {
          setActiveTab(catBlocks[0].category);
        }
        const arr = (pj.items || pj.data?.items || []).filter((p: any) => !p.is_deleted);
        setProjects(arr);
        setActiveAgents(agentState.items || agentState.data?.items || []);
      } catch (e: any) {
        message.error(e?.message || "加载 PMBOK / CPMAI 目录失败");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);

  const total = useMemo(() => categories.reduce((s, c) => s + c.count, 0), [categories]);

  const handleRun = (proc: PmbokProcess) => {
    setRunDialogAgent({ id: `pmbok:${proc.id}`, name: proc.name_cn, kind: "pmbok" });
    setRunDialogOpen(true);
  };

  // 手动运行统一由 AgentRunDialog 处理（检索 → 工具运用 → Markdown 结果）

  // ============ 深度编辑器逻辑 ============
  const openEditor = async (agent: AnyAgent | PmbokProcess, kind: "domain" | "pmbok") => {
    const id = (agent as any).id;
    const baseAgent: AnyAgent = {
      id,
      name: kind === "domain"
        ? (agent as AnyAgent).name
        : (agent as PmbokProcess).name_cn,
      name_en: (agent as any).name_en,
      description: kind === "domain"
        ? (agent as AnyAgent).description
        : (agent as PmbokProcess).summary,
      category: kind === "domain"
        ? (agent as AnyAgent).category
        : (agent as PmbokProcess).category,
      type: kind === "domain"
        ? (agent as AnyAgent).type
        : (agent as PmbokProcess).knowledge_area,
      icon: (agent as any).icon || "RobotOutlined",
      color: (agent as any).color || "#4F46E5",
      inputHint: (agent as any).inputHint || (agent as any).input_hint || "",
      tags: (agent as any).tags || [],
    };

    setEditing(baseAgent);
    setEditOverride(null);
    setEditBase(null);
    setEditOpen(true);
    setEditLoading(true);
    try {
      const res = await agentApi.getOverride(id);
      setEditOverride(res.override || {});
      setEditBase(res.base || null);
      // 初始化结构化 ITTO 编辑态（覆盖优先，否则用注册表默认）
      const ov = res.override || {};
      const base = res.base || {};
      setIttoInputs(ov.inputs_struct ?? base.inputs_struct ?? []);
      setIttoTools(ov.tools_struct ?? base.tools_struct ?? []);
      setIttoOutputs(ov.outputs_struct ?? base.outputs_struct ?? []);

      // 用 localStorage 草稿回显（如果存在）
      const draftKey = `agent_override_draft_${id}`;
      let draft: any = {};
      try { draft = JSON.parse(localStorage.getItem(draftKey) || "{}"); } catch {}

      const cur = {
        name: res.override?.name ?? baseAgent.name ?? "",
        description: res.override?.description ?? baseAgent.description ?? "",
        input_hint: res.override?.input_hint ?? baseAgent.inputHint ?? "",
        inputs: res.override?.inputs ?? (agent as any).inputs ?? [],
        tools: res.override?.tools ?? (agent as any).tools ?? [],
        outputs: res.override?.outputs ?? (agent as any).outputs ?? [],
        process: res.override?.process ?? (kind === "pmbok" ? (agent as PmbokProcess).v8 : "") ?? "",
        system_prompt: res.override?.system_prompt ?? "",
        note: draft.note || res.override?.note || "",
      };

      editForm.setFieldsValue({
        name: cur.name,
        description: cur.description,
        input_hint: cur.input_hint,
        process: cur.process || "",
        system_prompt: cur.system_prompt || "",
        note: cur.note || "",
      });
    } catch (e: any) {
      message.error(e?.message || "读取 Agent 配置失败");
    } finally {
      setEditLoading(false);
    }
  };

  const saveOverride = async () => {
    if (!editing) return;
    try {
      const v = await editForm.validateFields();
      setEditSaving(true);
      const payload = {
        name: v.name,
        description: v.description,
        input_hint: v.input_hint,
        // 结构化 ITTO（携带 optional / enabled 可配置项）
        inputs_struct: ittoInputs,
        tools_struct: ittoTools,
        outputs_struct: ittoOutputs,
        // 派生纯文本列表，供后端 get_structured_itto 的兼容分支使用
        inputs: ittoInputs.map((i) => i.label).filter(Boolean),
        tools: ittoTools.map((t) => t.label).filter(Boolean),
        outputs: ittoOutputs.map((o) => o.label).filter(Boolean),
        process: v.process,
        system_prompt: v.system_prompt,
        note: v.note,
      };
      const res = await agentApi.putOverride(editing.id, payload);
      // 同步本地草稿（用于下次打开恢复到表单 note）
      try { localStorage.setItem(`agent_override_draft_${editing.id}`, JSON.stringify({ note: v.note })); } catch {}
      message.success(`已保存 ${editing.name} 的个性化覆盖（${res.saved_at}）`);
      setDraftTick(t => t + 1);
    } catch (e: any) {
      if (e?.errorFields) {
        message.warning("请补齐必填字段");
      } else {
        message.error(e?.message || "保存失败");
      }
    } finally {
      setEditSaving(false);
    }
  };

  const resetOverride = async () => {
    if (!editing) return;
    Modal.confirm({
      title: "恢复内置默认值",
      content: `将删除 "${editing.name}" 的所有个性化覆盖，恢复为内置"完整可用"版本。继续吗？`,
      okType: "danger",
      onOk: async () => {
        try {
          await agentApi.deleteOverride(editing.id);
          // 清本地草稿
          try { localStorage.removeItem(`agent_override_draft_${editing.id}`); } catch {}
          message.success("已恢复内置默认值");
          setEditOpen(false);
        } catch (e: any) {
          message.error(e?.message || "恢复失败");
        }
      },
    });
  };

  const renderCard = (proc: PmbokProcess, color: string) => {
    const hasDraft = !!localStorage.getItem(`agent_override_draft_${proc.id}`);
    return (
      <List.Item>
        <Card
          size="small"
          hoverable
          style={{ borderRadius: 12, borderTop: `3px solid ${color}`, height: "100%" }}
          title={
            <Space style={{ width: "100%", justifyContent: "space-between" }}>
              <span>
                <Text strong>{proc.id}</Text>{" "}
                <Text>{proc.name_cn}</Text>
              </span>
              <Space size={4}>
                <Tooltip title="深度编辑（输入/工具/输出/过程）">
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => openEditor(proc, "pmbok")}
                  >编辑</Button>
                </Tooltip>
                <Button
                  type="primary"
                  size="small"
                  icon={<PlayCircleOutlined />}
                  loading={runDialogOpen && runDialogAgent?.id === `pmbok:${proc.id}`}
                  onClick={() => handleRun(proc)}
                >运行</Button>
                  <Tooltip title="物料驱动运行：检索输入 → 运用工具技术 → 输出 Markdown 结果">
                    <Button
                      size="small"
                      icon={<CloudDownloadOutlined />}
                      onClick={() => { setRunDialogAgent({ id: `pmbok:${proc.id}`, name: proc.name_cn, kind: "pmbok" }); setRunDialogOpen(true); }}
                    >物料运行</Button>
                  </Tooltip>
              </Space>
            </Space>
          }
        >
          <Space wrap style={{ marginBottom: 8 }}>
            <Tag color="purple"><PartitionOutlined /> {proc.knowledge_area}</Tag>
            <Tag>{proc.name_en}</Tag>
            {hasDraft && (
              <Tag color="orange" icon={<EditOutlined />}>本地草稿</Tag>
            )}
          </Space>
          {proc.summary && (
            <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 6 }}>
              {proc.summary}
            </Paragraph>
          )}
          <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 6 }}>
            <NodeIndexOutlined /> <b>输入/维度：</b>{proc.inputs.join("、") || "—"}
          </Paragraph>
          <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 6 }}>
            <ExperimentOutlined /> <b>工具/技术：</b>{proc.tools.join("、") || "—"}
          </Paragraph>
          <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 6 }}>
            <PartitionOutlined /> <b>输出：</b>{proc.outputs.join("、") || "—"}
          </Paragraph>
          {proc.v8 && (
            <Alert type="info" showIcon message={<span style={{ fontSize: 12 }}>{proc.v8}</span>}
              style={{ marginTop: 4, padding: "4px 8px" }} />
          )}
        </Card>
      </List.Item>
    );
  };

  const renderAgentCard = (ag: AnyAgent) => {
    return (
      <span
        key={ag.id}
        onClick={() => openEditor(ag, "domain")}
        style={{ display: "inline-block", cursor: "pointer" }}
      >
        <Tag
          style={{
            padding: "6px 10px",
            borderRadius: 8,
            background: "#FFF",
            border: `1px solid ${ag.color || "#4F46E5"}`,
            fontSize: 13,
          }}
        >
          <Space size={4}>
            <RobotOutlined style={{ color: ag.color }} />
            <span style={{ fontWeight: 500 }}>{ag.name}</span>
            {ag.type && <Tag color="blue" style={{ marginLeft: 4 }}>{ag.type}</Tag>}
            {ag.accuracy ? <Tooltip title={`准确度 ${ag.accuracy}%`}><Badge count={ag.accuracy} color="green" /></Tooltip> : null}
            <EditOutlined style={{ color: "#9CA3AF", marginLeft: 4 }} />
          </Space>
        </Tag>
      </span>
    );
  };

  // 统一渲染一组 ITTO：每项含「选用」Switch + 可编辑标签 + 删除；输入项额外含「可选/必需」Switch。
  const renderIttoCol = (
    kind: "input" | "tool" | "output",
    titleNode: React.ReactNode,
    desc: string,
    items: IttoItem[],
    setter: React.Dispatch<React.SetStateAction<IttoItem[]>>,
  ) => (
    <Col span={8}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text strong>{titleNode}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          已选用 {items.filter((i) => i.enabled !== false).length}/{items.length}
        </Text>
      </div>
      <Paragraph type="secondary" style={{ fontSize: 12, margin: "4px 0" }}>{desc}</Paragraph>
      <Space direction="vertical" style={{ width: "100%" }} size={6}>
        {items.length === 0 && <Text type="secondary">无</Text>}
        {items.map((it) => (
          <div
            key={it.key}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              opacity: it.enabled === false ? 0.5 : 1,
              background: "#FAFAFA",
              borderRadius: 6,
              padding: "4px 6px",
            }}
          >
            <Tooltip title="选用：关闭则该项不参与物料运行">
              <Switch
                size="small"
                checked={it.enabled !== false}
                onChange={(v) => patchItto(setter, it.key, { enabled: v })}
              />
            </Tooltip>
            <Input
              size="small"
              value={it.label}
              onChange={(e) => patchItto(setter, it.key, { label: e.target.value })}
              style={{ flex: 1 }}
              placeholder="条目名称"
            />
            {kind === "input" && (
              <Tooltip title="关闭=必需（缺失则阻塞运行）；开启=可选">
                <Space size={2}>
                  <Text type="secondary" style={{ fontSize: 11 }}>{it.optional ? "可选" : "必需"}</Text>
                  <Switch
                    size="small"
                    checked={!!it.optional}
                    onChange={(v) => patchItto(setter, it.key, { optional: v })}
                  />
                </Space>
              </Tooltip>
            )}
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => removeItto(setter, it.key)}
            />
          </div>
        ))}
      </Space>
      <Button
        size="small"
        type="dashed"
        block
        icon={<PlusOutlined />}
        style={{ marginTop: 8 }}
        onClick={() => addItto(setter, kind)}
      >新增条目</Button>
    </Col>
  );

  if (loading) {
    return <div style={{ padding: 48, textAlign: "center" }}><Spin /><p style={{ marginTop: 12 }}>加载知识单元目录…</p></div>;
  }

  return (
    <div style={{ padding: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <BookOutlined style={{ marginRight: 8, color: "#4F46E5" }} />
            Agent
          </Title>
          <Text type="secondary">
            汇总系统现有专业 Agent 与 PMBOK / CPMAI 知识单元，共 {total} 个知识单元。每个 Agent 默认完整可用（开箱即用），支持深度编辑输入 / 工具 / 输出 / 过程 / system_prompt 并持久化。
          </Text>
        </div>
        <Space>
          <Select
            style={{ width: 240 }}
            data-tour="agents-sel"
            placeholder="选择目标项目（可选）"
            allowClear
            value={projectId}
            onChange={setProjectId}
            options={projects.map((p: any) => ({ value: p.id, label: p.name }))}
          />
          {projectId && (
            <Button icon={<ProjectOutlined />} onClick={() => navigate(`/projects/${projectId}`)}>
              打开项目
            </Button>
          )}
        </Space>
      </div>

      {activeAgents.length > 0 && (
        <Card
          size="small"
          style={{ marginBottom: 16, borderRadius: 12 }}
          title={
            <Space>
              <RobotOutlined style={{ color: "#4F46E5" }} />
              <Text strong>专业 Agent（点击进入深度编辑）</Text>
              <Tag color="blue">{activeAgents.length}</Tag>
            </Space>
          }
          extra={
            <Tooltip title="所有 Agent 默认完整可用；编辑会保存到 backend/data/agent_overrides.json，可一键恢复">
              <Tag color="cyan" icon={<CheckOutlined />}>开箱即用</Tag>
            </Tooltip>
          }
        >
          <Space wrap>
            {activeAgents.map((agent) => renderAgentCard(agent))}
          </Space>
        </Card>
      )}


      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        data-tour="agents-tabs"
        items={categories.map(c => {
          const st = CAT_STYLE[c.category] || { color: "#4F46E5", icon: <BookOutlined /> };
          return {
            key: c.category,
            label: (
              <Space>
                <span style={{ color: st.color }}>{st.icon}</span>
                <span>{c.category}</span>
                <Tag color={st.color} style={{ borderRadius: 12, marginInlineEnd: 0 }}>{c.count}</Tag>
              </Space>
            ),
            children: (
              <List
                grid={{ gutter: 12, xs: 1, sm: 1, md: 2, lg: 2, xl: 3 }}
                dataSource={c.items}
                renderItem={(proc: PmbokProcess) => renderCard(proc, st.color)}
              />
            ),
          };
        })}
      />

      {/* 运行结果现由 AgentRunDialog 统一展示（Markdown + 检索/工具动画） */}

      {/* ============ Agent 深度编辑 Drawer ============ */}
      <Drawer
        title={
          <Space>
            <EditOutlined style={{ color: "#4F46E5" }} />
            <span>深度编辑 · {editing?.name || ""}</span>
            {editing && (
              <Tag color="purple" style={{ marginLeft: 4 }}>{editing.id}</Tag>
            )}
          </Space>
        }
        placement="right"
        width={680}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        destroyOnClose
        footer={
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <Space>
                <Tooltip title="运行此 Agent（检索输入 → 运用工具技术 → 输出 Markdown 结果）">
                  <Button
                    icon={<CloudDownloadOutlined />}
                    onClick={() => { setEditOpen(false); if (editing) { setRunDialogAgent({ id: editing.id, name: editing.name, kind: "domain" }); setRunDialogOpen(true); } }}
                  >
                    运行
                  </Button>
                </Tooltip>
              <Tooltip title="删除覆盖文件，恢复为内置默认（完整可用）">
                <Button danger icon={<DeleteOutlined />} onClick={resetOverride}>
                  恢复默认
                </Button>
              </Tooltip>
            </Space>
            <Space>
              <Button onClick={() => setEditOpen(false)}>关闭</Button>
              <Button type="primary" icon={<SaveOutlined />} loading={editSaving} onClick={saveOverride}>
                保存覆盖
              </Button>
            </Space>
          </Space>
        }
      >
        {editLoading ? (
          <div style={{ padding: 48, textAlign: "center" }}><Spin /></div>
        ) : (
          <>
            <Alert
              type="info"
              showIcon
              message="每个 Agent 默认完整可用"
              description={
                <span>
                  编辑修改输入 / 工具 / 输出 / 过程 / 系统提示词后，会以"覆盖"形式持久化到
                  <code style={{ padding: "0 4px" }}>backend/data/agent_overrides.json</code>，
                  不影响内置默认；可点底部「恢复默认」清空。
                </span>
              }
              style={{ marginBottom: 16 }}
            />

            {/* 基础信息 */}
            <Card type="inner" size="small" title={<><CodeOutlined /> 基础信息</>} style={{ marginBottom: 12 }}>
              <Form form={editForm} layout="vertical">
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item label="Agent 名称" name="name" rules={[{ required: true, message: "请输入名称" }]}>
                      <Input prefix={<RobotOutlined />} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="输入提示" name="input_hint" tooltip="用户在『运行』面板填写的输入字段说明">
                      <Input placeholder="例：项目 ID / 时间范围 / 风险关键词" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item label="描述" name="description">
                  <TextArea autoSize={{ minRows: 2, maxRows: 4 }} placeholder="Agent 用途的一句话总结" />
                </Form.Item>
              </Form>
            </Card>

            {/* ITTO（结构化 · 可配置） */}
            <Card
              type="inner"
              size="small"
              title={<><NodeIndexOutlined /> 输入 / 工具 / 输出（ITTO · 逐项选用 / 编辑）</>}
              style={{ marginBottom: 12 }}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>每项可开关选用、编辑标签、增删</Text>}
            >
              <Row gutter={16}>
                {renderIttoCol(
                  "input",
                  <><NodeIndexOutlined /> 输入（材料）</>,
                  "每项可「选用」；勾选「可选」则该输入缺失也不阻塞运行（默认必需）。",
                  ittoInputs,
                  setIttoInputs,
                )}
                {renderIttoCol(
                  "tool",
                  <><ToolOutlined /> 工具 / 技术</>,
                  "勾选要参与本次信息处理的工具技术（默认全选）。",
                  ittoTools,
                  setIttoTools,
                )}
                {renderIttoCol(
                  "output",
                  <><PartitionOutlined /> 输出（指定文件）</>,
                  "勾选需在运行时由 AI 生成并落盘的输出文件。",
                  ittoOutputs,
                  setIttoOutputs,
                )}
              </Row>
            </Card>

            {/* 过程展示 */}
            <Card type="inner" size="small" title={<><ExperimentOutlined /> 过程展示</>} style={{ marginBottom: 12 }}>
              <Form form={editForm} layout="vertical">
                <Form.Item
                  label="过程步骤 / PMBOK v8 对应说明"
                  name="process"
                  tooltip="Agent 实际执行的过程说明，或 PMBOK 第 8 版对应的描述"
                >
                  <TextArea autoSize={{ minRows: 3, maxRows: 8 }} placeholder="例：按照 PMBOK 第 8 版『规划』绩效域的『工作计划』原则 → 1. 启动 → 2. 分析 …" />
                </Form.Item>
              </Form>
            </Card>

            {/* 高级 system_prompt */}
            <Card type="inner" size="small" title={<><ThunderboltOutlined /> 高级 · System Prompt（可选）</>} style={{ marginBottom: 12 }}>
              <Form form={editForm} layout="vertical">
                <Form.Item
                  label="完整 system_prompt（覆盖后会拼接到 Agent 默认 prompt 之后）"
                  name="system_prompt"
                  tooltip="留空表示使用内置默认。"
                >
                  <TextArea
                    autoSize={{ minRows: 4, maxRows: 12 }}
                    placeholder={`例：\n你是「${editing?.name || '某Agent'}」专家。请基于项目上下文输出结构化建议，使用 Markdown 格式，按以下结构：\n- 结论\n- 输入依据\n- 风险与建议`}
                    style={{ fontFamily: "monospace", fontSize: 12 }}
                  />
                </Form.Item>
                <Form.Item label="本次编辑说明（仅本地草稿，不会上传）" name="note">
                  <Input placeholder="例：根据 7 月 25 日复盘调整输出格式" />
                </Form.Item>
              </Form>
            </Card>

            <Divider />
            <Text type="secondary" style={{ fontSize: 12 }}>
              已覆盖次数：{editOverride?.updated_at ? 1 : 0}（{editOverride?.updated_at || "尚未保存"} · {editOverride?.updated_by || "—"}）
            </Text>
          </>
        )}
      </Drawer>

      {/* ============ 统一手动运行对话框 ============ */}
      <AgentRunDialog
        open={runDialogOpen}
        onClose={() => setRunDialogOpen(false)}
        agent={runDialogAgent}
        projectId={projectId}
        projects={projects}
      />
    </div>
  );
};

export default PmbokAgents;
