import React, { useState } from 'react';
import { 
  Search, Sliders, Sparkles, Plus, Check, Bot, Zap,
  Layers, Send, Eye, Heart, MessageSquare, ChevronRight, ChevronLeft
} from 'lucide-react';
import { ResearchAsset, AssetSourceType } from '../types';
import { ImageWithFallback } from './ImageWithFallback';

interface SmartResearchHubProps {
  onPushToScript: (asset: ResearchAsset) => void;
  onSendToAgent: (prompt: string, asset: ResearchAsset) => void;
}

const SAMPLE_ASSETS: ResearchAsset[] = [
  {
    id: 'ast_reddit_1',
    title: 'Tại sao robot hình người năm 2026 đang thay đổi các nhà máy nhanh hơn dự đoán?',
    source: 'reddit',
    author: 'u/SingularityHub',
    url: 'https://reddit.com/r/technology/comments/robotics_2026',
    previewUrl: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '16:9',
    summary: 'Cuộc tranh luận sôi nổi về việc các tập đoàn sản xuất đang triển khai robot lao động giá rẻ thay vì công nhân có tay nghề.',
    score: 9.6,
    views: 420000,
    likes: 38500,
    comments: 4200,
    tags: ['Robotics', 'Future Tech', 'AI Automation'],
    branch: 'news',
    createdAgo: '2 giờ trước'
  },
  {
    id: 'ast_yt_1',
    title: 'Khám phá studio ảo Unreal Engine 5.5: Dựng phim Hollywood tại nhà chỉ bằng AI',
    source: 'youtube',
    author: 'Virtual Filmmakers',
    url: 'https://youtube.com/watch?v=unreal_studio_demo',
    previewUrl: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '16:9',
    summary: 'Quy trình tạo cảnh hành động kịch tính với ánh sáng Lumen và phông xanh ảo thời gian thực không cần render nặng.',
    score: 9.3,
    views: 890000,
    likes: 64000,
    comments: 3100,
    tags: ['VFX', 'Cinematic', 'Unreal Engine'],
    branch: 'art',
    createdAgo: '5 giờ trước'
  },
  {
    id: 'ast_tiktok_1',
    title: 'Biến hình phong cách Cyberpunk 2077 chỉ với hiệu ứng ánh sáng RGB neon',
    source: 'tiktok',
    author: '@neon_creator_vn',
    url: 'https://tiktok.com/@neon_creator_vn/video/rgb_aesthetic',
    previewUrl: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '9:16',
    summary: 'Tip quay video góc nghiêng với bóng đèn led ống đổi màu tạo cảm giác phim khoa học viễn tưởng trong phòng ngủ.',
    score: 8.9,
    views: 1250000,
    likes: 195000,
    comments: 5400,
    tags: ['Shorts Viral', 'Cyberpunk', 'Lighting'],
    branch: 'entertainment',
    createdAgo: '45 phút trước'
  },
  {
    id: 'ast_news_1',
    title: 'Kỷ nguyên chip 2nm chính thức thương mại hóa: Cuộc đua bán dẫn toàn cầu bước vào ngã rẽ mới',
    source: 'news',
    author: 'TechNews Asia',
    url: 'https://example.com/news/chip-2nm-commercial',
    previewUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '16:9',
    summary: 'Các nhà máy đúc chip tại châu Á đồng loạt công bố kế hoạch xuất xưởng chip tiến trình mới cho smartphone và trung tâm dữ liệu AI.',
    score: 9.1,
    views: 280000,
    likes: 18200,
    comments: 1100,
    tags: ['Semiconductor', 'AI Chips', 'Global Tech'],
    branch: 'news',
    createdAgo: '3 giờ trước'
  },
  {
    id: 'ast_twitter_1',
    title: 'Chiến thuật phản công chớp nhoáng của các CLB châu Âu mùa giải 2026',
    source: 'twitter',
    author: '@TacticsZone',
    url: 'https://x.com/TacticsZone/status/counter_tactics',
    previewUrl: 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '1:1',
    summary: 'Biểu đồ nhiệt và video phân tích sự chuyển dịch từ kiểm soát bóng sang pressing định hướng không gian của các HLV hàng đầu.',
    score: 8.7,
    views: 610000,
    likes: 47000,
    comments: 2900,
    tags: ['Football', 'Tactics', 'Sports Analysis'],
    branch: 'sports',
    createdAgo: '6 giờ trước'
  },
  {
    id: 'ast_tiktok_2',
    title: 'Nghệ thuật vẽ tranh ảo 3D ngoài trời khiến hàng triệu người qua đường ngỡ ngàng',
    source: 'tiktok',
    author: '@streetart_3d',
    url: 'https://tiktok.com/@streetart_3d/video/optical_illusion',
    previewUrl: 'https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=600&q=80',
    aspectRatio: '9:16',
    summary: 'Tranh vẽ phối cảnh anamorphic biến vỉa hè phẳng thành hố sâu không đáy và thác nước chân thực.',
    score: 9.4,
    views: 2400000,
    likes: 310000,
    comments: 8900,
    tags: ['Art Illusion', 'Street Art', 'Creative'],
    branch: 'art',
    createdAgo: '1 giờ trước'
  }
];

export const SmartResearchHub: React.FC<SmartResearchHubProps> = ({
  onPushToScript,
  onSendToAgent
}) => {
  const [topicInput, setTopicInput] = useState('Xu hướng AI và Robot 2026');
  const [activeBranch, setActiveBranch] = useState<'entertainment' | 'art' | 'sports' | 'news' | 'custom'>('news');
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false);
  
  const [sources, setSources] = useState({
    tiktok: { enabled: true, weight: 85, name: 'MXH (TikTok, Reels, X)' },
    reddit: { enabled: true, weight: 95, name: 'Forum/Groups (Reddit, FB)' },
    news: { enabled: true, weight: 70, name: 'Báo chí / Website' },
    youtube: { enabled: true, weight: 90, name: 'YouTube Shorts & Video' }
  });

  const [pushedIds, setPushedIds] = useState<Set<string>>(new Set());

  const [chatMessages, setChatMessages] = useState<Array<{ role: 'ai' | 'user'; text: string }>>([
    {
      role: 'ai',
      text: 'Xin chào! Tôi đã quét qua các nguồn xu hướng cho chủ đề "' + topicInput + '". Bạn muốn phân tích góc nhìn tranh cãi trên Reddit, hay tìm các hook mở đầu video ngắn?'
    }
  ]);
  const [userInput, setUserInput] = useState('');
  const [isAiTyping, setIsAiTyping] = useState(false);

  const nicheKeywords = [
    'Humanoid Robots 2026', 'Cybernetic Aesthetics', 'Unreal Engine 5.5',
    'AI Sound Design', 'Chip 2nm Mass Production', 'Anamorphic Illusion',
    'High Velocity Content', 'A/B Hook Matrix'
  ];

  const handlePush = (asset: ResearchAsset) => {
    onPushToScript(asset);
    setPushedIds(prev => new Set(prev).add(asset.id));
    setTimeout(() => {
      setPushedIds(prev => {
        const next = new Set(prev);
        next.delete(asset.id);
        return next;
      });
    }, 2500);
  };

  const handleSendMessage = () => {
    if (!userInput.trim()) return;
    const msg = userInput;
    setUserInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    setIsAiTyping(true);

    setTimeout(() => {
      let reply = '';
      const lower = msg.toLowerCase();
      if (lower.includes('reddit') || lower.includes('tranh cãi') || lower.includes('ý kiến')) {
        reply = '📌 **Tóm tắt luồng ý kiến trên Reddit (r/technology & r/singularity):**\n- **Nhóm Ủng hộ (60%):** Tự động hóa giúp giảm 70% chi phí sản xuất và tạo ra các nhà máy không ngủ 24/7.\n- **Nhóm Hoài nghi (40%):** Lo ngại về tỷ lệ lỗi phần mềm cơ khí và sự phụ thuộc vào chuỗi cung ứng chip độc quyền.';
      } else if (lower.includes('hook') || lower.includes('mở đầu') || lower.includes('kịch bản')) {
        reply = '💡 **3 Hook mở đầu video giữ chân người xem cực tốt:**\n1. *"DỪNG LẠI! 90% mọi người đang không nhận ra sự thay đổi khủng khiếp này..."*\n2. *"Liệu AI có thể thay thế hoàn toàn công việc sáng tạo của bạn trước năm 2027?"*\n3. *"Một tài liệu bí mật vừa bị rò rỉ sáng nay và đây là sự thật..."*';
      } else {
        reply = `Phân tích cho "${msg}": Tỷ lệ tương tác đang tăng mạnh ở định dạng video ngắn 9:16 (Save rate đạt 18.5%). Tôi khuyên bạn nên tập trung vào góc nhìn thực tế và so sánh trực quan.`;
      }
      setChatMessages(prev => [...prev, { role: 'ai', text: reply }]);
      setIsAiTyping(false);
    }, 600);
  };

  const getSourceBadgeStyle = (source: AssetSourceType) => {
    switch (source) {
      case 'reddit':
        return 'text-orange-700 bg-orange-50 border-orange-200';
      case 'youtube':
        return 'text-red-700 bg-red-50 border-red-200';
      case 'tiktok':
        return 'text-pink-700 bg-pink-50 border-pink-200';
      case 'news':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'twitter':
        return 'text-sky-700 bg-sky-50 border-sky-200';
      default:
        return 'text-amber-700 bg-amber-50 border-amber-200';
    }
  };

  const filteredAssets = SAMPLE_ASSETS.filter(a => {
    if (activeBranch !== 'custom' && a.branch !== activeBranch) {
      return true; // Keep accessible
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* ================= TOP BAR: BỘ LỌC THÔNG MINH ================= */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          {/* Input Topic */}
          <div className="lg:col-span-6">
            <label className="text-xs font-semibold text-stone-600 block mb-1.5 flex items-center space-x-1.5">
              <Search className="w-3.5 h-3.5 text-orange-600" />
              <span>Chủ đề cần thu thập (Input Topic):</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder="Nhập từ khóa chủ đề (VD: Trí tuệ nhân tạo, Robot hình người, Tài chính GenZ)..."
                className="w-full bg-orange-50/30 border border-orange-200 rounded-xl px-4 py-2.5 text-sm text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white focus:ring-2 focus:ring-orange-500/20 font-medium transition-all"
              />
              <button 
                onClick={() => setTopicInput(topicInput)}
                className="absolute right-2 top-2 px-3 py-1 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold shadow-xs transition-colors"
              >
                Quét Trend
              </button>
            </div>
          </div>

          {/* Branch Selector Tabs */}
          <div className="lg:col-span-6">
            <label className="text-xs font-semibold text-stone-600 block mb-1.5">
              Phân loại nhánh nội dung (Branch Selector):
            </label>
            <div className="flex flex-wrap gap-1 bg-stone-100/80 p-1.5 rounded-xl border border-stone-200/80">
              {[
                { id: 'entertainment', label: '1. Giải trí & MXH' },
                { id: 'art', label: '2. Nghệ thuật' },
                { id: 'sports', label: '3. Thể thao' },
                { id: 'news', label: '4. Tin tức' },
                { id: 'custom', label: '5. Tùy chỉnh' }
              ].map((b) => (
                <button
                  key={b.id}
                  onClick={() => setActiveBranch(b.id as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                    activeBranch === b.id
                      ? 'bg-white text-orange-700 font-bold shadow-xs border border-orange-200/70'
                      : 'text-stone-600 hover:text-stone-900 hover:bg-white/60'
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Source Prioritization (Checkboxes & Weight Sliders) */}
        <div className="pt-3 border-t border-orange-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-stone-800 flex items-center space-x-1.5">
              <Sliders className="w-3.5 h-3.5 text-orange-600" />
              <span>Độ ưu tiên nguồn dữ liệu & Trọng số phân bổ (Source Weights):</span>
            </span>
            <span className="text-[11px] text-stone-500">
              Tự động phân bổ crawl và xếp hạng video tiềm năng
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* TikTok */}
            <div className="bg-stone-50/80 border border-stone-200/80 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center space-x-2 cursor-pointer text-stone-800 font-semibold">
                  <input
                    type="checkbox"
                    checked={sources.tiktok.enabled}
                    onChange={(e) => setSources(s => ({ ...s, tiktok: { ...s.tiktok, enabled: e.target.checked } }))}
                    className="rounded text-orange-600 focus:ring-orange-500"
                  />
                  <span>MXH (TikTok, Reels, X)</span>
                </label>
                <span className="font-mono text-pink-600 font-bold tabular-nums">{sources.tiktok.weight}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={sources.tiktok.weight}
                disabled={!sources.tiktok.enabled}
                onChange={(e) => setSources(s => ({ ...s, tiktok: { ...s.tiktok, weight: parseInt(e.target.value) } }))}
                className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600 disabled:opacity-30"
              />
            </div>

            {/* Reddit */}
            <div className="bg-stone-50/80 border border-stone-200/80 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center space-x-2 cursor-pointer text-stone-800 font-semibold">
                  <input
                    type="checkbox"
                    checked={sources.reddit.enabled}
                    onChange={(e) => setSources(s => ({ ...s, reddit: { ...s.reddit, enabled: e.target.checked } }))}
                    className="rounded text-orange-600 focus:ring-orange-500"
                  />
                  <span>Forum/Groups (Reddit, FB)</span>
                </label>
                <span className="font-mono text-orange-600 font-bold tabular-nums">{sources.reddit.weight}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={sources.reddit.weight}
                disabled={!sources.reddit.enabled}
                onChange={(e) => setSources(s => ({ ...s, reddit: { ...s.reddit, weight: parseInt(e.target.value) } }))}
                className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600 disabled:opacity-30"
              />
            </div>

            {/* News */}
            <div className="bg-stone-50/80 border border-stone-200/80 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center space-x-2 cursor-pointer text-stone-800 font-semibold">
                  <input
                    type="checkbox"
                    checked={sources.news.enabled}
                    onChange={(e) => setSources(s => ({ ...s, news: { ...s.news, enabled: e.target.checked } }))}
                    className="rounded text-orange-600 focus:ring-orange-500"
                  />
                  <span>Báo chí / Website</span>
                </label>
                <span className="font-mono text-emerald-600 font-bold tabular-nums">{sources.news.weight}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={sources.news.weight}
                disabled={!sources.news.enabled}
                onChange={(e) => setSources(s => ({ ...s, news: { ...s.news, weight: parseInt(e.target.value) } }))}
                className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600 disabled:opacity-30"
              />
            </div>

            {/* YouTube */}
            <div className="bg-stone-50/80 border border-stone-200/80 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="flex items-center space-x-2 cursor-pointer text-stone-800 font-semibold">
                  <input
                    type="checkbox"
                    checked={sources.youtube.enabled}
                    onChange={(e) => setSources(s => ({ ...s, youtube: { ...s.youtube, enabled: e.target.checked } }))}
                    className="rounded text-orange-600 focus:ring-orange-500"
                  />
                  <span>YouTube Shorts & Video</span>
                </label>
                <span className="font-mono text-red-600 font-bold tabular-nums">{sources.youtube.weight}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={sources.youtube.weight}
                disabled={!sources.youtube.enabled}
                onChange={(e) => setSources(s => ({ ...s, youtube: { ...s.youtube, weight: parseInt(e.target.value) } }))}
                className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600 disabled:opacity-30"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ================= 3-COLUMN WORKSPACE: CANVAS + AI ASSISTANT ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* CENTER CANVAS: ASSET GRID (8 Cols or 12 Cols if panel collapsed) */}
        <div className={`space-y-4 transition-all duration-300 ${isPanelCollapsed ? 'lg:col-span-12' : 'lg:col-span-8'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-orange-600" />
              <h3 className="text-sm font-bold text-stone-900">
                Kho Asset Thu Thập ({filteredAssets.length} kết quả tuyển chọn)
              </h3>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-stone-500 hidden sm:inline">
                Hover card để đẩy vào Kịch bản hoặc tạo biến thể qua Agent
              </span>
              {isPanelCollapsed && (
                <button
                  onClick={() => setIsPanelCollapsed(false)}
                  className="flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-orange-700 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-lg"
                >
                  <Bot className="w-3.5 h-3.5 text-orange-600" />
                  <span>Mở Trợ Lý AI</span>
                </button>
              )}
            </div>
          </div>

          {/* Masonry-Style Grid */}
          <div className={`grid gap-4 ${isPanelCollapsed ? 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2'}`}>
            {filteredAssets.map((asset) => {
              const isPushed = pushedIds.has(asset.id);
              return (
                <div
                  key={asset.id}
                  className="group relative bg-white border border-orange-200/70 hover:border-orange-400 rounded-2xl overflow-hidden transition-all duration-300 shadow-xs hover:shadow-lg hover:shadow-orange-500/10 flex flex-col"
                >
                  {/* Media Thumbnail with Source Badge */}
                  <div className="relative h-44 w-full bg-stone-100 overflow-hidden">
                    <ImageWithFallback
                      src={asset.previewUrl}
                      alt={asset.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />

                    {/* Source Color Badge */}
                    <div className="absolute top-3 left-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border backdrop-blur-md shadow-xs ${getSourceBadgeStyle(asset.source)}`}>
                        {asset.source}
                      </span>
                    </div>

                    {/* Score Tag */}
                    <div className="absolute top-3 right-3 bg-white/95 backdrop-blur-md text-amber-600 border border-amber-200 font-mono font-bold text-xs px-2 py-0.5 rounded-lg shadow-xs flex items-center space-x-1">
                      <span>★ {asset.score}</span>
                    </div>

                    {/* Hover Action Overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-stone-900/90 via-stone-900/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3 space-y-2">
                      <div className="flex items-center space-x-2">
                        {/* Push to Script Action */}
                        <button
                          onClick={() => handlePush(asset)}
                          className={`flex-1 flex items-center justify-center space-x-1.5 py-2 px-3 rounded-xl text-xs font-bold transition-all shadow-md ${
                            isPushed
                              ? 'bg-emerald-600 text-white'
                              : 'bg-orange-600 hover:bg-orange-500 text-white'
                          }`}
                        >
                          {isPushed ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-white" />
                              <span>Đã vào Script!</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3.5 h-3.5" />
                              <span>Đẩy vào Script</span>
                            </>
                          )}
                        </button>

                        {/* Generate Variation via Agent */}
                        <button
                          onClick={() => onSendToAgent(`Tạo biến thể hình ảnh góc nhìn điện ảnh từ: ${asset.title}`, asset)}
                          className="flex items-center justify-center p-2 rounded-xl bg-white text-orange-600 hover:bg-orange-50 transition-all shadow-md"
                          title="Tạo biến thể qua Local Agent"
                        >
                          <Sparkles className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-4 flex-grow flex flex-col justify-between space-y-2.5">
                    <div>
                      <h4 className="font-bold text-sm text-stone-900 group-hover:text-orange-600 transition-colors line-clamp-2 leading-snug">
                        {asset.title}
                      </h4>
                      <p className="text-xs text-stone-500 mt-1 line-clamp-2 leading-relaxed">
                        {asset.summary}
                      </p>
                    </div>

                    {/* Clean unboxed tags */}
                    <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-stone-500">
                      {asset.tags.map((tag, i) => (
                        <span key={i} className="text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded text-[10px]">
                          #{tag}
                        </span>
                      ))}
                    </div>

                    {/* Footer Metrics */}
                    <div className="pt-2.5 border-t border-stone-100 flex items-center justify-between text-[11px] text-stone-500">
                      <span className="font-medium text-stone-700">{asset.author}</span>
                      <div className="flex items-center space-x-3 tabular-nums">
                        <span className="flex items-center space-x-1">
                          <Eye className="w-3 h-3 text-stone-400" />
                          <span>{(asset.views / 1000).toFixed(0)}k</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Heart className="w-3 h-3 text-pink-500" />
                          <span>{(asset.likes / 1000).toFixed(0)}k</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <MessageSquare className="w-3 h-3 text-orange-500" />
                          <span>{asset.comments}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT PANEL: AI RESEARCH ASSISTANT (4 Cols) */}
        {!isPanelCollapsed && (
          <div className="lg:col-span-4 bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs flex flex-col h-[740px] sticky top-20">
            <div className="flex items-center justify-between border-b border-orange-100 pb-3 mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-orange-100 text-orange-600 flex items-center justify-center font-bold">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-stone-900">AI Research Assistant</h3>
                  <div className="text-[10px] text-emerald-700 flex items-center font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1" />
                    <span>Gemini Trend Intelligence</span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsPanelCollapsed(true)}
                className="text-stone-400 hover:text-stone-700 p-1 rounded-md"
                title="Thu gọn panel"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Niche Keywords Chips */}
            <div className="mb-3">
              <label className="text-[11px] font-semibold text-stone-600 block mb-1.5 flex items-center space-x-1">
                <Zap className="w-3 h-3 text-amber-500" />
                <span>Gợi ý từ khóa ngách (Niche Keywords):</span>
              </label>
              <div className="flex flex-wrap gap-1">
                {nicheKeywords.map((kw, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setTopicInput(kw);
                      setUserInput(`Phân tích cơ hội làm video viral cho từ khóa: "${kw}"`);
                    }}
                    className="text-[10px] bg-orange-50/70 hover:bg-orange-100 text-stone-700 hover:text-orange-800 border border-orange-200/60 px-2 py-0.5 rounded transition-colors"
                  >
                    +{kw}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Messages Log */}
            <div className="flex-grow overflow-y-auto space-y-3 pr-1 text-xs">
              {chatMessages.map((m, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border leading-relaxed ${
                    m.role === 'ai'
                      ? 'bg-orange-50/40 border-orange-100 text-stone-800'
                      : 'bg-orange-600 text-white border-transparent ml-4'
                  }`}
                >
                  <div className={`text-[10px] font-bold uppercase mb-1 ${m.role === 'ai' ? 'text-orange-700' : 'text-orange-100'}`}>
                    {m.role === 'ai' ? '🤖 Trợ lý nghiên cứu' : '👤 Bạn'}
                  </div>
                  <div className="whitespace-pre-line">{m.text}</div>
                </div>
              ))}
              {isAiTyping && (
                <div className="bg-orange-50/50 border border-orange-100 p-3 rounded-xl text-xs text-stone-500 flex items-center space-x-2">
                  <Sparkles className="w-3.5 h-3.5 animate-spin text-orange-500" />
                  <span>Đang tổng hợp các luồng dữ liệu...</span>
                </div>
              )}
            </div>

            {/* Quick Prompts Bar */}
            <div className="pt-2 border-t border-orange-100 space-y-2 mt-2">
              <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-[11px]">
                <button
                  onClick={() => {
                    setUserInput('Tóm tắt các luồng ý kiến trái chiều về chủ đề này trên Reddit');
                  }}
                  className="whitespace-nowrap px-2 py-1 rounded bg-stone-100 text-stone-600 hover:text-stone-900 hover:bg-stone-200"
                >
                  Tóm tắt Reddit
                </button>
                <button
                  onClick={() => {
                    setUserInput('Đề xuất 3 hook mở đầu video ngắn giữ chân người xem');
                  }}
                  className="whitespace-nowrap px-2 py-1 rounded bg-stone-100 text-stone-600 hover:text-stone-900 hover:bg-stone-200"
                >
                  Gợi ý 3 Hook
                </button>
              </div>

              {/* Input & Send */}
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Hỏi AI hoặc yêu cầu phân tích kịch bản..."
                  className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!userInput.trim() || isAiTyping}
                  className="p-2 rounded-xl bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-40 transition-colors shadow-xs"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
