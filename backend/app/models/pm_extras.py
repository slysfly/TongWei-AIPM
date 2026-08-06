"""经验教训 / 变更控制 数据库模型

字段命名与前端页面完全一致（to_dict 输出 camelCase），避免脆弱映射。
"""
import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.session import Base


def _uuid():
    return str(uuid.uuid4())


class Lesson(Base):
    """经验教训登记册（Lessons Learned）"""
    __tablename__ = "lessons_learned"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_name = Column(String(255), default="")
    category = Column(String(64), default="项目管理")
    title = Column(String(512), nullable=False)
    description = Column(Text, default="")
    what_went_well = Column(Text, default="")
    what_could_improve = Column(Text, default="")
    action_items = Column(Text, default="")
    rating = Column(Integer, default=3)
    created_by = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "projectName": self.project_name or "",
            "category": self.category or "",
            "title": self.title,
            "description": self.description or "",
            "whatWentWell": self.what_went_well or "",
            "whatCouldImprove": self.what_could_improve or "",
            "actionItems": self.action_items or "",
            "rating": self.rating or 0,
            "createdBy": self.created_by or "",
            "createdAt": self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
        }


class ChangeRequest(Base):
    """变更控制（Change Control / CCB）"""
    __tablename__ = "change_requests"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    project_name = Column(String(255), default="")  # 冗余存储，便于直接展示
    title = Column(String(512), nullable=False)
    description = Column(Text, default="")
    reason = Column(Text, default="")
    impact = Column(Text, default="")
    priority = Column(String(32), default="medium")
    status = Column(String(32), default="submitted")
    category = Column(String(64), default="范围变更")
    requested_by = Column(String(128), default="")
    approved_by = Column(String(128), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(String(32), default="")

    # ── 结构化变更明细 + 执行结果（CCB 强校验） ────────────────────────────────
    # change_items: 由提交人填写的"由什么变为什么"列表，每项含
    #   {scope, entity_type("project"|"task"|"milestone"), entity_id,
    #    entity_label, field, field_label, before, after}
    change_items = Column(JSON, default=list)
    # execution_log: 审批通过后由 AI 执行器生成，每项含
    #   {scope, entity_type, entity_id, field, before, after,
    #    applied(bool), verified(bool), applied_at, error}
    execution_log = Column(JSON, default=list)

    def to_dict(self):
        return {
            "id": self.id,
            "projectId": self.project_id or "",
            "projectName": self.project_name or "",
            "title": self.title,
            "description": self.description or "",
            "reason": self.reason or "",
            "impact": self.impact or "",
            "priority": self.priority or "medium",
            "status": self.status or "submitted",
            "category": self.category or "",
            "requestedBy": self.requested_by or "",
            "approvedBy": self.approved_by or "",
            "createdAt": self.created_at.strftime("%Y-%m-%d") if self.created_at else "",
            "resolvedAt": self.resolved_at or "",
            "changeItems": list(self.change_items or []),
            "executionLog": list(self.execution_log or []),
        }
