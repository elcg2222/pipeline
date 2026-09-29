import React, { useState } from 'react';
import { 
  Play, Download, CheckCircle2, Send, RotateCcw, 
  ExternalLink, Search, PlusCircle, Check, 
  Sparkles, RefreshCw, Terminal, Clock,
  Video, Eye, Heart, Bookmark, BarChart2
} from 'lucide-react';
import { VideoItem, RunItem } from '../types';

interface PipelineMonitorProps {
  videos: VideoItem[];
  runs: RunItem[];
  summary: {
    states: Record<string, number>;
    platforms: Record<string, number>;
    job: {
      command: string | null;
      started: number | null;
      output: string;
    };
  };
  onRunCommand: (command: string, urls?: string[]) => Promise<void>;
  isLoading: boolean;
  refreshData: () => Promise<void>;
}

export const PipelineMonitor: React.FC<PipelineMonitorProps> = ({
  videos,
  runs,
  summary,
  onRunCommand,
  isLoading,
  refreshData
}) => {
  const [platformFilter, setPlatformFilter] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [manualUrls, setManualUrls] = useState('');
  const [showConsole, setShowConsole] = useState(true);
  const [copiedUid, setCopiedUid] = useState<string | null>(null);

  const detectPlatforms = (text: string) => {
    const urls = text.split(/\s+/).filter(Boolean);
    const set = new Set<string>();
    for (const url of urls) {
      if (/tiktok\.com/.test(url)) set.add('TikTok');
      else if (/douyin\.com/.test(url)) set.add('Douyin');
      else if (/youtube\.com|youtu\.be/.test(url)) set.add('YouTube');
      else if (/instagram\.com/.test(url)) set.add('Instagram');
      else if (/reddit\.com|redd\.it/.test(url)) set.add('Reddit');
      else if (/facebook\.com|fb\.watch/.test(url)) set.add('Facebook');
      else set.add('Web khác');
    }
    return Array.from(set);
  };

  const handleAddUrls = async () => {
    const urls = manualUrls.split(/\s+/).filter(u => u.startsWith('http://') || u.startsWith('https://'));
    if (urls.length === 0) {
      alert('Vui lòng nhập ít nhất một URL hợp lệ bắt đầu bằng https://');
      return;
    }
    await onRunCommand('add', urls);
    setManualUrls('');
  };

  const detected = detectPlatforms(manualUrls);

  const filteredVideos = videos.filter(v => {
    if (platformFilter && v.platform !== platformFilter) return false;
    if (stateFilter && v.state !== stateFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match = (v.title && v.title.toLowerCase().includes(q)) ||
                    (v.author && v.author.toLowerCase().includes(q)) ||
                    (v.topic && v.topic.toLowerCase().includes(q)) ||
                    v.uid.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const getStateBadgeStyle = (state: string) => {
    switch (state) {
      case 'qc_passed':
      case 'dubbed':
      case 'published':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'downloading':
      case 'queued':
      case 'discovered':
        return 'text-orange-700 bg-orange-50 border-orange-200';
      case 'error':
      case 'qc_failed':
      case 'rejected':
        return 'text-rose-700 bg-rose-50 border-rose-200';
      default:
        return 'text-stone-700 bg-stone-100 border-stone-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* State Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
        {Object.entries(summary.states).map(([state, count]) => (
          <div 
            key={state}
            onClick={() => setStateFilter(stateFilter === state ? '' : state)}
            className={`p-3 rounded-xl border cursor-pointer transition-all ${
              stateFilter === state 
                ? 'bg-orange-50 border-orange-500 ring-2 ring-orange-500/20 shadow-xs' 
                : 'bg-white border-orange-200/80 hover:border-orange-300 shadow-2xs'
            }`}
          >
            <div className="text-xl font-bold text-stone-900 tabular-nums">{count}</div>
            <div className="text-xs text-stone-500 capitalize mt-0.5 truncate">{state.replace('_', ' ')}</div>
          </div>
        ))}
      </div>

      {/* Pipeline Toolbar */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-orange-100 pb-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-700">
              Tác vụ Pipeline & Điều khiển:
            </span>
          </div>
          <button 
            onClick={refreshData}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-stone-100 text-xs font-semibold text-stone-700 hover:bg-stone-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Làm mới</span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            disabled={!!summary.job.command}
            onClick={() => onRunCommand('discover')}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-orange-600 hover:bg-orange-700 text-white font-semibold text-xs shadow-xs transition-all disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Quét nguồn</span>
          </button>

          <button
            disabled={!!summary.job.command}
            onClick={() => onRunCommand('download')}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-xs transition-all disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Tải video</span>
          </button>

          <button
            disabled={!!summary.job.command}
            onClick={() => onRunCommand('qc')}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-xs transition-all disabled:opacity-50"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Chạy QC (VAD+pHash)</span>
          </button>

          <button
            disabled={!!summary.job.command}
            onClick={() => onRunCommand('export')}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-xs transition-all disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Xuất AutoDub</span>
          </button>

          <button
            disabled={!!summary.job.command}
            onClick={() => onRunCommand('all')}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Chạy Toàn Bộ Luồng</span>
          </button>
        </div>

        {/* Input Manual URLs Box */}
        <div className="pt-2 border-t border-orange-100 flex flex-col sm:flex-row gap-3 items-center">
          <input
            type="text"
            value={manualUrls}
            onChange={(e) => setManualUrls(e.target.value)}
            placeholder="Dán link video TikTok, Douyin, YouTube Shorts, Reels để nạp vào hệ thống..."
            className="w-full bg-stone-50 border border-orange-200 rounded-xl px-4 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
          />
          <button
            onClick={handleAddUrls}
            disabled={!manualUrls.trim()}
            className="px-4 py-2 rounded-xl bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold shrink-0 disabled:opacity-40"
          >
            + Nạp Video
          </button>
        </div>
      </div>

      {/* Videos List Table */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-bold text-stone-900">
              Danh Sách Video Trong Kho SQLite ({filteredVideos.length} mục)
            </h3>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo tiêu đề, tác giả..."
              className="bg-stone-50 border border-stone-200 rounded-lg px-3 py-1.5 text-xs text-stone-900 focus:outline-none focus:border-orange-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-stone-700">
            <thead className="bg-stone-50 border-y border-stone-200 text-stone-500 uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-3">UID</th>
                <th className="py-2.5 px-3">Nền Tảng</th>
                <th className="py-2.5 px-3">Tiêu Đề</th>
                <th className="py-2.5 px-3">Tác Giả</th>
                <th className="py-2.5 px-3 text-right">Lượt Xem</th>
                <th className="py-2.5 px-3">Trạng Thái</th>
                <th className="py-2.5 px-3 text-right">Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {filteredVideos.slice(0, 50).map((v) => (
                <tr key={v.uid} className="hover:bg-orange-50/40 transition-colors">
                  <td className="py-2 px-3 font-mono text-[11px] text-stone-500">{v.uid.slice(0, 10)}...</td>
                  <td className="py-2 px-3 font-semibold text-stone-800">{v.platform}</td>
                  <td className="py-2 px-3 max-w-[280px] truncate font-medium text-stone-900">{v.title || 'Không có tiêu đề'}</td>
                  <td className="py-2 px-3 text-stone-500">{v.author || 'N/A'}</td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums text-stone-700">{(v.views || 0).toLocaleString()}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getStateBadgeStyle(v.state)}`}>
                      {v.state}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right">
                    <a href={v.url} target="_blank" rel="noreferrer" className="text-orange-600 hover:text-orange-700 font-semibold text-xs">
                      Mở ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
