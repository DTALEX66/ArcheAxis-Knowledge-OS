import { useAaosTheme } from '../design-system/ThemeProvider';
import { AAOS_THEME_REGISTRY } from '../design-system/theme';
import './BrandHeader.css';

interface BrandHeaderProps {
  title: string;
  subtitle?: string;
  showQuickActions?: boolean;
  onNewDocument?: () => void;
  onImportFile?: () => void;
}

export function BrandHeader({
  title,
  subtitle,
  showQuickActions = false,
  onNewDocument,
  onImportFile
}: BrandHeaderProps) {
  const { theme } = useAaosTheme();
  return (
    <div className="brand-header">
      <div className="brand-header-left">
        <img
          src={AAOS_THEME_REGISTRY[theme].brandMark}
          alt="ArcheAxis"
          className="brand-logo"
        />
        <div className="brand-header-text">
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>

      {showQuickActions && (
        <div className="brand-header-actions">
          {onNewDocument && (
            <button
              className="header-action-btn primary"
              onClick={onNewDocument}
            >
              <span className="btn-icon">+</span>
              新建文档
            </button>
          )}
          {onImportFile && (
            <button
              className="header-action-btn secondary"
              onClick={onImportFile}
            >
              <span className="btn-icon">↑</span>
              导入文件
            </button>
          )}
        </div>
      )}
    </div>
  );
}
