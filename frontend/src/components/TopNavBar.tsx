import { useAaosTheme } from '../design-system/ThemeProvider';
import { AAOS_THEME_REGISTRY } from '../design-system/theme';
import './TopNavBar.css';
import { DiagnosticCenterTrigger } from './DiagnosticConsole';
import { commandKeyLabel } from '../presentation/keyboardShortcuts';

interface Breadcrumb {
  label: string;
  onClick?: () => void;
}

interface TopNavBarProps {
  breadcrumbs: Breadcrumb[];
  onSearch?: () => void;
  onSettings?: () => void;
  notificationCount?: number;
  userName?: string;
}

export function TopNavBar({
  breadcrumbs,
  onSearch,
  onSettings,
  notificationCount = 0,
  userName = 'User'
}: TopNavBarProps) {
  const { theme } = useAaosTheme();

  return (
    <>
      <nav className="top-nav-bar">
        <div className="top-nav-container">
          {/* Left: Logo + Breadcrumbs */}
          <div className="top-nav-left">
            <img
              src={AAOS_THEME_REGISTRY[theme].brandMark}
              alt="ArcheAxis"
              className="top-nav-logo"
            />
            <div className="top-nav-breadcrumb">
              {breadcrumbs.map((crumb, index) => (
                <span key={index}>
                  {index > 0 && (
                    <span className="breadcrumb-separator">/</span>
                  )}
                  <span
                    className={`breadcrumb-item ${
                      index === breadcrumbs.length - 1 ? 'current' : ''
                    }`}
                  >
                    {crumb.onClick ? (
                      <button onClick={crumb.onClick}>
                        {crumb.label}
                      </button>
                    ) : (
                      crumb.label
                    )}
                  </span>
                </span>
              ))}
            </div>
          </div>

          {/* Center: Search */}
          <div className="top-nav-center">
            <button
              className="top-nav-search-trigger"
              type="button"
              aria-label="搜索页面、能力与内容"
              aria-keyshortcuts="Control+K Meta+K"
              onClick={onSearch}
            >
              <span className="search-trigger-icon">🔍</span>
              <span className="search-trigger-text">
                搜索文档、知识、学习内容...
              </span>
              <div className="search-trigger-shortcut">
                <span className="search-trigger-key">{commandKeyLabel()}</span>
                <span className="search-trigger-key">K</span>
              </div>
            </button>
          </div>

          {/* Right: Actions */}
          <div className="top-nav-right">
            <DiagnosticCenterTrigger />
            <button
              className={`top-nav-action ${notificationCount > 0 ? 'has-badge' : ''}`}
              aria-label="通知"
              title="通知"
            >
              🔔
            </button>

            <button
              className="top-nav-action"
              aria-label="设置"
              title="设置"
              type="button"
              onClick={onSettings}
            >
              ⚙️
            </button>

            <button className="top-nav-user">
              <div className="top-nav-avatar">
                {userName.charAt(0).toUpperCase()}
              </div>
            </button>
          </div>
        </div>
      </nav>

    </>
  );
}
