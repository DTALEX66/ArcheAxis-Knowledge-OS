// Bottom activity dock: conversion/verify/index/import-export (task pack §15.3).
export function ActivityDock() {
  return (
    <footer className="activity-dock" aria-label="活动坞">
      <span className="activity-dock-item" data-disabled="true">
        转换
      </span>
      <span className="activity-dock-item" data-disabled="true">
        核验
      </span>
      <span className="activity-dock-item" data-disabled="true">
        索引
      </span>
      <span className="activity-dock-item" data-disabled="true">
        导入 / 导出
      </span>
    </footer>
  );
}
