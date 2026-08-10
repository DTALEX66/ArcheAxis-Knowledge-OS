# 组件库

## Shell

- `AppShell`
- `GlobalTopBar`
- `PrimarySidebar`
- `ProjectSpaceList`
- `GlobalCommandBar`
- `EnvironmentChip`
- `ModelRouteChip`
- `NotificationButton`
- `UserMenu`
- `StatusBar`
- `CognitiveInspector`

## Data Display

- `MetricCard`
- `StatusBadge`
- `ProgressBar`
- `DonutMetric`
- `Sparkline`
- `DataTable`
- `EmptyState`
- `ErrorState`
- `CapabilityBoundary`
- `SourceList`
- `EvidenceList`
- `AuditTimeline`

## Agent/Task

- `AgentCard`
- `AgentDetailDrawer`
- `TaskRow`
- `TaskStageRail`
- `TaskExecutionCard`
- `SubtaskList`
- `ApprovalCard`
- `ArtifactStrip`
- `ActionCapabilityBar`

## Research/Knowledge

- `ResearchPackageCard`
- `ClaimRow`
- `EvidenceStrength`
- `ConflictBadge`
- `UnknownBadge`
- `KnowledgeTree`
- `KnowledgeEditor`
- `RelationCard`
- `QualityMeter`

## Canvas/Replay

- `CanvasNode`
- `CanvasEdge`
- `MiniMap`
- `NodeInspector`
- `ReplayControls`
- `ReplayEvent`
- `EvidenceSnapshot`

## Component Rules

1. 所有可执行按钮必须绑定真实 action capability。
2. 进度条必须由后端提供可验证的分子/分母或明确阶段。
3. 表格必须有 Loading/Empty/Error。
4. Drawer/Inspector 必须可键盘关闭。
5. 颜色不能是唯一状态表达。
6. 组件不得显示内部 ID。
