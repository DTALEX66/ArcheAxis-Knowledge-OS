import { useState, useEffect } from 'react';
import { BRAND_ASSETS } from '../assets/index';
import { GlobalSearch } from './GlobalSearch';
import './TopNavBar.css';

interface Breadcrumb {
  label: string;
  onClick?: () => void;
}

interface TopNavBarProps {
  breadcrumbs: Breadcrumb[];
  onSearch?: () => void;
  notificationCount?: number;
  userName?: string;
}

export function TopNavBar({
  breadcrumbs,
  onSearch,
  notificationCount = 0,
  userName = 'User'
}: TopNavBarProps) {
  const [searchOpen, setSearchOpen] = useState(false);

  const handleSearchTrigger = () => {
    setSearchOpen(true);
    onSearch?.();
  };

  const handleSearchSelect = (result: any) => {
    console.log('Selected:', result);
    // TODO: 导航到选中的结果
  };

  // Cmd+K 快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        handleSearchTrigger();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  return (
    <>
      <nav className="top-nav-bar">
        <div className="top-nav-container">
          {/* Left: Logo + Breadcrumbs */}
          <div className="top-nav-left">
            <img
              src={BRAND_ASSETS.logo.white}
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
              onClick={handleSearchTrigger}
            >
              <span className="search-trigger-icon">🔍</span>
              <span className="search-trigger-text">
                搜索文档、知识、学习内容...
              </span>
              <div className="search-trigger-shortcut">
                <span className="search-trigger-key">⌘</span>
                <span className="search-trigger-key">K</span>
              </div>
            </button>
          </div>

          {/* Right: Actions */}
          <div className="top-nav-right">
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

      {/* Global Search Modal */}
      <GlobalSearch
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={handleSearchSelect}
      />
    </>
  );
}
