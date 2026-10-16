import { useEffect, useState, useRef } from 'react';
import './GlobalSearch.css';

interface SearchResult {
  id: string;
  type: 'document' | 'knowledge' | 'conversation' | 'learning';
  title: string;
  content?: string;
  breadcrumb?: string[];
  icon?: string;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (result: SearchResult) => void;
}

export function GlobalSearch({ isOpen, onClose, onSelect }: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (results[selectedIndex]) {
            onSelect(results[selectedIndex]);
            onClose();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex, onClose, onSelect]);

  const handleSearch = (value: string) => {
    setQuery(value);
    setSelectedIndex(0);

    // TODO: 实际调用搜索API
    // 这里是模拟数据
    if (value.trim()) {
      const mockResults: SearchResult[] = [
        {
          id: '1',
          type: 'document' as const,
          title: '品牌研究报告.pdf',
          content: '包含品牌定位和市场分析',
          breadcrumb: ['知识库', '市场研究'],
          icon: '📄'
        },
        {
          id: '2',
          type: 'knowledge' as const,
          title: 'ArcheAxis 产品规划',
          content: '本地优先的知识操作系统',
          breadcrumb: ['知识', '产品'],
          icon: '💡'
        },
        {
          id: '3',
          type: 'learning' as const,
          title: 'React Hooks 学习',
          content: '进度: 75% 完成',
          breadcrumb: ['学习', '前端开发'],
          icon: '📚'
        }
      ].filter(r =>
        r.title.toLowerCase().includes(value.toLowerCase()) ||
        r.content?.toLowerCase().includes(value.toLowerCase())
      );
      setResults(mockResults);
    } else {
      setResults([]);
    }
  };

  if (!isOpen) return null;

  const groupedResults = results.reduce((acc, result) => {
    if (!acc[result.type]) acc[result.type] = [];
    acc[result.type].push(result);
    return acc;
  }, {} as Record<string, SearchResult[]>);

  const typeLabels = {
    document: '文档',
    knowledge: '知识',
    conversation: 'AI对话',
    learning: '学习'
  };

  return (
    <div className="global-search-overlay" onClick={onClose}>
      <div className="global-search-modal" onClick={e => e.stopPropagation()}>
        <div className="global-search-input-wrapper">
          <span className="global-search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => handleSearch(e.target.value)}
            placeholder="搜索文档、知识、学习内容..."
            className="global-search-input"
          />
          <span className="global-search-shortcut">Esc</span>
        </div>

        <div className="global-search-results">
          {results.length === 0 ? (
            <div className="search-empty">
              <div className="search-empty-icon">🔍</div>
              <p>
                {query ? '没有找到匹配的内容' : '输入关键词开始搜索'}
              </p>
            </div>
          ) : (
            Object.entries(groupedResults).map(([type, items]) => (
              <div key={type} className="search-results-group">
                <div className="search-results-group-title">
                  {typeLabels[type as keyof typeof typeLabels]}
                </div>
                {items.map((result) => {
                  const globalIndex = results.indexOf(result);
                  return (
                    <div
                      key={result.id}
                      className={`search-result-item ${
                        globalIndex === selectedIndex ? 'selected' : ''
                      }`}
                      onClick={() => {
                        onSelect(result);
                        onClose();
                      }}
                    >
                      <div className="search-result-icon">
                        {result.icon || '📄'}
                      </div>
                      <div className="search-result-content">
                        <div className="search-result-title">
                          {result.title}
                        </div>
                        {result.content && (
                          <div className="search-result-meta">
                            {result.content}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="search-footer">
          <div className="search-footer-shortcuts">
            <span className="search-footer-shortcut">
              <span className="search-footer-key">↑↓</span> 导航
            </span>
            <span className="search-footer-shortcut">
              <span className="search-footer-key">Enter</span> 打开
            </span>
            <span className="search-footer-shortcut">
              <span className="search-footer-key">Esc</span> 关闭
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
