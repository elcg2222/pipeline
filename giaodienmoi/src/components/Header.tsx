import React from 'react';
import { 
  Activity, Send, RefreshCw, Layers, 
  Search, Cpu, Scissors, Sparkles, Flame, Rocket
} from 'lucide-react';

export type TabType = 'research' | 'storyboard' | 'batch' | 'command' | 'editor' | 'monitor' | 'handoff';

interface HeaderProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  totalVideos: number;
  totalPassed: number;
  totalProjects: number;
  isProcessing: boolean;
  agentConnected: boolean;
  activeBatchCount?: number;
  onOpenBatchWizard?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  totalVideos,
  totalPassed,
  totalProjects,
  isProcessing,
  agentConnected,
  activeBatchCount = 0,
  onOpenBatchWizard
}) => {
  return (
    <header className="border-b border-orange-200/80 bg-white/95 sticky top-0 z-30 shadow-sm backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
        {/* Brand Zone */}
        <div className="flex items-center space-x-3 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-orange-600 via-orange-500 to-amber-500 flex items-center justify-center text-white shadow-md shadow-orange-500/25">
            <Flame className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-base font-bold text-stone-900 tracking-tight">
                Social Video Studio
              </span>
              <span className="text-[10px] font-semibold text-orange-600 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded">
                Batch Engine 3.0
              </span>
            </div>
            <div className="text-[11px] text-stone-500 flex items-center space-x-1.5">
              <span>Quy trình sản xuất video hàng loạt tự động</span>
              <span aria-hidden="true">·</span>
              <span className="text-emerald-700 font-medium">GPU Local Sẵn Sàng</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs (Numbered step-by-step for clear mental model) */}
        <nav className="hidden lg:flex items-center space-x-1 bg-stone-100/80 p-1 rounded-xl border border-stone-200/70">
          <button
            onClick={() => setActiveTab('research')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'research'
                ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/80'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>1 · Smart Hub</span>
          </button>

          <button
            onClick={() => setActiveTab('storyboard')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'storyboard'
                ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/80'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>2 · Storyboard</span>
          </button>

          <button
            onClick={() => setActiveTab('batch')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'batch'
                ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20'
                : 'text-orange-700 hover:text-orange-800 hover:bg-orange-50'
            }`}
          >
            <Rocket className="w-3.5 h-3.5 text-amber-500" />
            <span>3 · Tạo Hàng Loạt</span>
            {activeBatchCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-orange-600 text-white text-[9px] flex items-center justify-center font-bold">
                {activeBatchCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('command')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'command'
                ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/80'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>4 · Local Agent GPU</span>
          </button>

          <button
            onClick={() => setActiveTab('editor')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'editor'
                ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm shadow-orange-500/20'
                : 'text-stone-600 hover:text-stone-900 hover:bg-white/80'
            }`}
          >
            <Scissors className="w-3.5 h-3.5" />
            <span>5 · Mini Editor</span>
          </button>

          <div className="h-4 w-px bg-stone-300 mx-1" />

          <button
            onClick={() => setActiveTab('monitor')}
            className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              activeTab === 'monitor'
                ? 'bg-white text-stone-900 shadow-xs border border-stone-200'
                : 'text-stone-500 hover:text-stone-900'
            }`}
            title="Kho SQLite database"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Database</span>
          </button>

          <button
            onClick={() => setActiveTab('handoff')}
            className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
              activeTab === 'handoff'
                ? 'bg-white text-stone-900 shadow-xs border border-stone-200'
                : 'text-stone-500 hover:text-stone-900'
            }`}
            title="Kaggle Flow3 ZIP"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Kaggle ZIP</span>
          </button>
        </nav>

        {/* Action Zone: 1-Click Batch Wizard & Telemetry status */}
        <div className="flex items-center space-x-3">
          {onOpenBatchWizard && (
            <button
              onClick={onOpenBatchWizard}
              className="flex items-center space-x-1.5 px-3.5 py-2 text-xs font-bold text-white bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 rounded-lg shadow-sm shadow-orange-500/25 transition-all transform active:scale-95 whitespace-nowrap"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Tạo 10 Video 1-Click</span>
            </button>
          )}

          {isProcessing && (
            <span className="flex items-center text-xs text-orange-700 bg-orange-50 border border-orange-200 px-2 py-1 rounded-md">
              <RefreshCw className="w-3 h-3 mr-1 animate-spin text-orange-600" />
              Đang render
            </span>
          )}
        </div>
      </div>

      {/* Mobile Navigation bar */}
      <div className="lg:hidden border-t border-orange-100 px-3 py-2 flex items-center space-x-1 overflow-x-auto bg-stone-50">
        <button
          onClick={() => setActiveTab('research')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'research' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          1 · Hub
        </button>
        <button
          onClick={() => setActiveTab('storyboard')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'storyboard' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          2 · Storyboard
        </button>
        <button
          onClick={() => setActiveTab('batch')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'batch' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          3 · Batch Matrix
        </button>
        <button
          onClick={() => setActiveTab('command')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'command' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          4 · Agent GPU
        </button>
        <button
          onClick={() => setActiveTab('editor')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'editor' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          5 · Editor
        </button>
        <button
          onClick={() => setActiveTab('monitor')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'monitor' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          DB
        </button>
        <button
          onClick={() => setActiveTab('handoff')}
          className={`px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap ${
            activeTab === 'handoff' ? 'bg-orange-500 text-white' : 'text-stone-600'
          }`}
        >
          Kaggle
        </button>
      </div>
    </header>
  );
};
