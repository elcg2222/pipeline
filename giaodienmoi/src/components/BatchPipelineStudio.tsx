import React, { useState } from 'react';
import { 
  Rocket, Sparkles, Check, Download,
  Sliders, Film, Wand2, RefreshCw, Play, Pause,
  Share2, Zap, ArrowRight, CheckCircle2, ShieldCheck, MonitorPlay
} from 'lucide-react';
import { BatchVideoVariant, SceneItem } from '../types';
import { ImageWithFallback } from './ImageWithFallback';

interface BatchPipelineStudioProps {
  baseScenes: SceneItem[];
  projectName: string;
  onSendBatchToColab: (variants: BatchVideoVariant[]) => void;
}

export const BatchPipelineStudio: React.FC<BatchPipelineStudioProps> = ({
  baseScenes,
  projectName,
  onSendBatchToColab
}) => {
  // Sub-Flow view tabs
  const [pipelineView, setPipelineView] = useState<'matrix' | 'autopilot' | 'platforms'>('matrix');

  // Config Matrix Options
  const [selectedHooks, setSelectedHooks] = useState<string[]>(['shock', 'question', 'negative']);
  const [selectedStyles, setSelectedStyles] = useState<string[]>(['cinematic', 'cyberpunk']);
  const [selectedVoices, setSelectedVoices] = useState<string[]>(['male_warm', 'female_bright']);
  const [captionsStyle, setCaptionsStyle] = useState<'hormozi' | 'gold_glow' | 'minimal_orange' | 'karaoke'>('hormozi');
  const [targetRatio, setTargetRatio] = useState<'9:16' | '16:9'>('9:16');

  // Auto-Pilot Pipeline Steps
  const [pipelineSteps, setPipelineSteps] = useState([
    { id: 'step_crawl', name: '1. Quét Trend & Hook', status: 'completed', desc: 'Đã thu thập 12 video thịnh hành từ TikTok & Reddit' },
    { id: 'step_script', name: '2. AI Viết Kịch Bản A/B', status: 'completed', desc: 'Đã tạo 5 kịch bản phân nhánh theo 5 góc nhìn' },
    { id: 'step_voice', name: '3. Tổng Hợp Giọng TTS Đa Miền', status: 'in_progress', desc: 'Đang tổng hợp 3 giọng (Bắc, Trung, Nam)' },
    { id: 'step_visual', name: '4. Sinh Ảnh B-Roll Local Agent', status: 'queued', desc: 'Sẵn sàng đẩy 16 prompt sang GPU RTX 4090' },
    { id: 'step_render', name: '5. Render Video & Xuất Colab', status: 'queued', desc: 'Gói Remotion / CapCut JSON tự động' }
  ]);
  const [isAutoPilotRunning, setIsAutoPilotRunning] = useState(false);

  // Generated Variants List
  const [variants, setVariants] = useState<BatchVideoVariant[]>([
    {
      id: 'var_01',
      title: `${projectName} - Biến thể #1 (Shock Hook · Cinematic)`,
      hookType: 'shock',
      hookText: 'DỪNG LẠI! 90% mọi người đang không nhận ra sự thay đổi khủng khiếp này...',
      visualStyle: 'cinematic',
      voicePreset: 'Aoede (Nam Bắc Trầm)',
      captionsStyle: 'hormozi',
      aspectRatio: '9:16',
      status: 'ready',
      progress: 100,
      duration: 28,
      thumbnailUrl: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80',
      targetPlatforms: ['tiktok', 'youtube', 'reels']
    },
    {
      id: 'var_02',
      title: `${projectName} - Biến thể #2 (Question Hook · Cyberpunk)`,
      hookType: 'question',
      hookText: 'Liệu AI có thể thay thế hoàn toàn công việc sáng tạo của bạn trước năm 2027?',
      visualStyle: 'cyberpunk',
      voicePreset: 'Kore (Nữ Nam Trong trẻo)',
      captionsStyle: 'hormozi',
      aspectRatio: '9:16',
      status: 'ready',
      progress: 100,
      duration: 32,
      thumbnailUrl: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80',
      targetPlatforms: ['tiktok', 'reels']
    },
    {
      id: 'var_03',
      title: `${projectName} - Biến thể #3 (Negative Hook · Hollywood)`,
      hookType: 'negative',
      hookText: 'Đừng bao giờ bỏ qua công nghệ này nếu bạn không muốn bị bỏ lại phía sau!',
      visualStyle: 'cinematic',
      voicePreset: 'Puck (Nam Hype TikTok)',
      captionsStyle: 'gold_glow',
      aspectRatio: '9:16',
      status: 'rendering',
      progress: 64,
      duration: 30,
      thumbnailUrl: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80',
      targetPlatforms: ['youtube', 'tiktok']
    },
    {
      id: 'var_04',
      title: `${projectName} - Biến thể #4 (Story Hook · 3D Style)`,
      hookType: 'story',
      hookText: 'Ngày hôm qua, một thử nghiệm ngầm vừa được công bố và nó đã thay đổi tất cả...',
      visualStyle: 'photorealistic',
      voicePreset: 'Aoede (Nam Bắc Trầm)',
      captionsStyle: 'minimal_orange',
      aspectRatio: '9:16',
      status: 'queued',
      progress: 10,
      duration: 26,
      thumbnailUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80',
      targetPlatforms: ['tiktok', 'youtube', 'reels', 'facebook']
    }
  ]);

  const [activePreviewVariant, setActivePreviewVariant] = useState<BatchVideoVariant>(variants[0]);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const [isGeneratingMatrix, setIsGeneratingMatrix] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  // Hook presets dictionary
  const hookOptions = [
    { id: 'shock', label: '1. Shock / Giật gân', sample: 'Bạn sẽ không tin vào mắt mình khi nhìn thấy điều này...' },
    { id: 'question', label: '2. Câu hỏi tò mò', sample: 'Tại sao 95% mọi người lại đang hiểu sai điều này?' },
    { id: 'negative', label: '3. Cảnh báo / Tiêu cực', sample: 'Dừng ngay nếu bạn đang làm theo cách truyền thống...' },
    { id: 'story', label: '4. Câu chuyện mở đầu', sample: 'Một tài liệu nội bộ vừa bị rò rỉ sáng nay...' },
    { id: 'statistic', label: '5. Số liệu gây sốc', sample: 'Chỉ sau 24 giờ, con số này đã tăng vọt 400%...' }
  ];

  // Visual style presets
  const styleOptions = [
    { id: 'cinematic', label: 'Điện ảnh Hollywood 35mm' },
    { id: 'cyberpunk', label: 'Cyberpunk Neon Ánh Sáng' },
    { id: 'anime', label: 'Anime / 3D Stylized' },
    { id: 'photorealistic', label: 'Siêu thực tế 8K (Photorealistic)' }
  ];

  // Generate Matrix Action
  const handleGenerateMatrix = () => {
    setIsGeneratingMatrix(true);

    setTimeout(() => {
      const generated: BatchVideoVariant[] = [];
      let count = 1;

      for (const hookId of selectedHooks) {
        for (const styleId of selectedStyles) {
          if (count > 6) break;
          const hookInfo = hookOptions.find(h => h.id === hookId);
          generated.push({
            id: `var_${Date.now()}_${count}`,
            title: `${projectName} · Biến thể #${count} (${hookInfo?.label.split('.')[1].trim()})`,
            hookType: hookId as any,
            hookText: hookInfo?.sample || 'Mở đầu video gây ấn tượng mạnh...',
            visualStyle: styleId as any,
            voicePreset: count % 2 === 0 ? 'Kore (Nữ Nam)' : 'Aoede (Nam Bắc)',
            captionsStyle: captionsStyle,
            aspectRatio: targetRatio,
            status: count <= 2 ? 'ready' : 'rendering',
            progress: count <= 2 ? 100 : 35,
            duration: 25 + Math.floor(Math.random() * 10),
            thumbnailUrl: count % 2 === 0
              ? 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80'
              : 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80',
            targetPlatforms: ['tiktok', 'youtube', 'reels']
          });
          count++;
        }
      }

      setVariants(generated);
      setActivePreviewVariant(generated[0]);
      setIsGeneratingMatrix(false);
    }, 700);
  };

  // Run Auto-Pilot sequence
  const handleRunAutoPilot = () => {
    setIsAutoPilotRunning(true);
    let stepIdx = 2; // step 3 in progress
    const timer = setInterval(() => {
      setPipelineSteps(prev => prev.map((step, idx) => {
        if (idx === stepIdx) return { ...step, status: 'completed' };
        if (idx === stepIdx + 1) return { ...step, status: 'in_progress' };
        return step;
      }));
      stepIdx++;
      if (stepIdx >= 5) {
        clearInterval(timer);
        setIsAutoPilotRunning(false);
        // Set all variants to ready
        setVariants(prev => prev.map(v => ({ ...v, status: 'ready', progress: 100 })));
      }
    }, 1500);
  };

  const handleDownloadAll = () => {
    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 2500);
    onSendBatchToColab(variants);
  };

  const readyCount = variants.filter(v => v.status === 'ready').length;

  return (
    <div className="space-y-6">
      {/* Top Banner with Orange Theme */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-500 via-orange-600 to-amber-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
            <Rocket className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-stone-900">
                Batch Video Pipeline Studio (Tạo Video Hàng Loạt Tự Động)
              </h2>
              <span className="text-[10px] font-bold text-orange-700 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded">
                Anti-Duplicate Engine
              </span>
            </div>
            <div className="text-xs text-stone-500 mt-0.5 flex items-center space-x-1.5">
              <span>1 Kịch bản</span>
              <span aria-hidden="true">➔</span>
              <span>Ma trận 5-10 Hook & Style</span>
              <span aria-hidden="true">➔</span>
              <span>A/B Testing Đa Nền Tảng (TikTok / YouTube / Reels)</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-xs text-stone-600">
            Đã hoàn thành: <span className="font-bold text-emerald-700 tabular-nums">{readyCount}</span> / {variants.length} video
          </div>

          <button
            onClick={handleDownloadAll}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs shadow-xs transition-all active:scale-95"
          >
            {downloadSuccess ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Đã chuẩn bị gói Batch Colab!</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>📦 Xuất toàn bộ {variants.length} video sang Colab</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sub-Flow Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-orange-200/80 pb-3">
        <div className="flex items-center space-x-2 bg-stone-100/80 p-1 rounded-xl border border-stone-200/80">
          <button
            onClick={() => setPipelineView('matrix')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              pipelineView === 'matrix'
                ? 'bg-white text-orange-700 shadow-xs border border-orange-200/70 font-bold'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            ⚡ 1. Ma Trận Biến Thể (Matrix A/B)
          </button>
          <button
            onClick={() => setPipelineView('autopilot')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              pipelineView === 'autopilot'
                ? 'bg-white text-orange-700 shadow-xs border border-orange-200/70 font-bold'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            🤖 2. Auto-Pilot Pipeline 5 Bước
          </button>
          <button
            onClick={() => setPipelineView('platforms')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              pipelineView === 'platforms'
                ? 'bg-white text-orange-700 shadow-xs border border-orange-200/70 font-bold'
                : 'text-stone-600 hover:text-stone-900'
            }`}
          >
            📱 3. Auto-Reframe & An Toàn Safe-Zone
          </button>
        </div>

        <span className="text-xs text-stone-500 hidden sm:inline">
          {pipelineView === 'matrix' && 'Thiết lập nhân bản biến thể tự động'}
          {pipelineView === 'autopilot' && 'Quy trình chạy tuần tự từ Crawl đến Export'}
          {pipelineView === 'platforms' && 'Kiểm tra tỷ lệ hiển thị chữ không bị che nút like/share'}
        </span>
      </div>

      {/* VIEW 1: MATRIX ENGINE */}
      {pipelineView === 'matrix' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* ================= LEFT COLUMN: MATRIX CONFIG (5 Cols) ================= */}
          <div className="lg:col-span-5 bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-orange-100 pb-3">
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider flex items-center space-x-1.5">
                <Sliders className="w-4 h-4 text-orange-600" />
                <span>Thiết lập Ma Trận Nhân Bản (Matrix Config)</span>
              </h3>
              <span className="text-[11px] text-orange-600 font-mono font-bold tabular-nums">
                ~{selectedHooks.length * selectedStyles.length} video
              </span>
            </div>

            {/* 1. Chọn Hook mở đầu */}
            <div>
              <label className="text-xs font-semibold text-stone-700 block mb-1.5">
                1. Chọn các biến thể Hook mở đầu (Giữ chân 3s):
              </label>
              <div className="space-y-1.5">
                {hookOptions.map((hook) => {
                  const checked = selectedHooks.includes(hook.id);
                  return (
                    <div
                      key={hook.id}
                      onClick={() => {
                        if (checked) {
                          if (selectedHooks.length > 1) setSelectedHooks(selectedHooks.filter(h => h !== hook.id));
                        } else {
                          setSelectedHooks([...selectedHooks, hook.id]);
                        }
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                        checked
                          ? 'bg-orange-50/80 border-orange-400 text-stone-900 ring-1 ring-orange-500/20'
                          : 'bg-stone-50/60 border-stone-200 text-stone-600 hover:border-orange-300 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between font-semibold">
                        <span>{hook.label}</span>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {}}
                          className="rounded text-orange-600 focus:ring-orange-500"
                        />
                      </div>
                      <p className="text-[11px] text-stone-500 mt-0.5 italic truncate">
                        "{hook.sample}"
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 2. Visual Styles */}
            <div>
              <label className="text-xs font-semibold text-stone-700 block mb-1.5">
                2. Phong cách đồ họa & B-Roll (Visual Styles):
              </label>
              <div className="grid grid-cols-2 gap-2">
                {styleOptions.map((st) => {
                  const checked = selectedStyles.includes(st.id);
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => {
                        if (checked) {
                          if (selectedStyles.length > 1) setSelectedStyles(selectedStyles.filter(s => s !== st.id));
                        } else {
                          setSelectedStyles([...selectedStyles, st.id]);
                        }
                      }}
                      className={`p-2 rounded-xl border text-xs font-medium text-left transition-all ${
                        checked
                          ? 'bg-orange-50/80 border-orange-400 text-orange-900 font-semibold'
                          : 'bg-stone-50/60 border-stone-200 text-stone-600 hover:border-orange-300'
                      }`}
                    >
                      {st.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Phụ đề Auto-Captions Style */}
            <div>
              <label className="text-xs font-semibold text-stone-700 block mb-1.5">
                3. Phong cách phụ đề động (Auto-Captions):
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'hormozi', name: '🔥 Alex Hormozi (Chữ nhảy từ)' },
                  { id: 'gold_glow', name: '✨ Cinematic Gold Glow' },
                  { id: 'minimal_orange', name: '🟧 Minimalist Sunset' },
                  { id: 'karaoke', name: '🎤 Karaoke Highlight' }
                ].map((cap) => (
                  <button
                    key={cap.id}
                    onClick={() => setCaptionsStyle(cap.id as any)}
                    className={`p-2 rounded-xl border text-xs text-left transition-all ${
                      captionsStyle === cap.id
                        ? 'bg-orange-100/80 border-orange-500 text-orange-900 font-bold'
                        : 'bg-stone-50/60 border-stone-200 text-stone-600 hover:border-orange-300'
                    }`}
                  >
                    {cap.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Action Button: Sinh ma trận */}
            <button
              onClick={handleGenerateMatrix}
              disabled={isGeneratingMatrix}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-orange-500 via-orange-600 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-bold text-xs shadow-md shadow-orange-500/20 transition-all flex items-center justify-center space-x-2 active:scale-95"
            >
              {isGeneratingMatrix ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Đang tính toán ma trận và sinh biến thể...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  <span>⚡ Sinh ma trận {selectedHooks.length * selectedStyles.length} biến thể video ngay</span>
                </>
              )}
            </button>
          </div>

          {/* ================= RIGHT COLUMN: BATCH RENDER QUEUE & PREVIEW (7 Cols) ================= */}
          <div className="lg:col-span-7 bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-orange-100 pb-3">
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider flex items-center space-x-1.5">
                <Film className="w-4 h-4 text-orange-600" />
                <span>Hàng đợi video đã sinh ({variants.length} biến thể)</span>
              </h3>
              <span className="text-[11px] text-stone-500">
                Bấm vào từng mục để xem mô phỏng phát
              </span>
            </div>

            {/* Active Preview Showcase */}
            {activePreviewVariant && (
              <div className="bg-stone-50 border border-orange-200 rounded-xl p-4 flex flex-col sm:flex-row gap-4 items-center">
                <div className="relative w-32 aspect-[9/16] bg-stone-900 rounded-lg overflow-hidden border border-stone-800 shrink-0 shadow-md">
                  <ImageWithFallback
                    src={activePreviewVariant.thumbnailUrl}
                    alt={activePreviewVariant.title}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 flex flex-col justify-between p-2 pointer-events-none">
                    <span className="bg-orange-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded uppercase self-start">
                      {activePreviewVariant.hookType}
                    </span>
                    <div className="text-center">
                      <span className="bg-amber-400 text-stone-900 text-[9px] font-extrabold px-1.5 py-0.5 rounded shadow-xs">
                        {activePreviewVariant.captionsStyle.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Play preview toggle button */}
                  <button
                    onClick={() => setIsPlayingPreview(!isPlayingPreview)}
                    className="absolute inset-0 m-auto w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center transition-all"
                  >
                    {isPlayingPreview ? (
                      <Pause className="w-4 h-4 fill-white" />
                    ) : (
                      <Play className="w-4 h-4 fill-white ml-0.5" />
                    )}
                  </button>
                </div>

                <div className="flex-grow space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-stone-900 text-sm">
                      {activePreviewVariant.title}
                    </h4>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {activePreviewVariant.status}
                    </span>
                  </div>

                  <p className="text-orange-950 text-xs bg-orange-50/80 p-2.5 rounded-lg border border-orange-200/70 italic leading-relaxed">
                    Hook: "{activePreviewVariant.hookText}"
                  </p>

                  <div className="grid grid-cols-2 gap-2 text-[11px] text-stone-600">
                    <div>Phong cách: <span className="text-stone-900 font-semibold capitalize">{activePreviewVariant.visualStyle}</span></div>
                    <div>Giọng đọc: <span className="text-stone-900 font-semibold">{activePreviewVariant.voicePreset}</span></div>
                    <div>Thời lượng: <span className="text-stone-900 font-mono font-semibold tabular-nums">{activePreviewVariant.duration}s</span></div>
                    <div>Tỉ lệ: <span className="text-stone-900 font-mono font-semibold">{activePreviewVariant.aspectRatio}</span></div>
                  </div>

                  {/* Platforms target tags */}
                  <div className="flex items-center space-x-1.5 pt-1">
                    <span className="text-[11px] text-stone-500 font-medium">Tối ưu cho:</span>
                    {activePreviewVariant.targetPlatforms.map(p => (
                      <span key={p} className="text-[10px] uppercase font-bold text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded border border-orange-200">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Variants Queue List */}
            <div className="space-y-2 overflow-y-auto max-h-[360px] pr-1">
              {variants.map((v) => (
                <div
                  key={v.id}
                  onClick={() => setActivePreviewVariant(v)}
                  className={`p-3 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                    activePreviewVariant?.id === v.id
                      ? 'bg-orange-50/70 border-orange-400 ring-1 ring-orange-500/20'
                      : 'bg-stone-50/60 border-stone-200/80 hover:border-orange-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center space-x-3 truncate">
                    <div className="w-10 h-10 rounded-lg overflow-hidden shrink-0 border border-stone-200">
                      <ImageWithFallback
                        src={v.thumbnailUrl}
                        alt={v.title}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-bold text-stone-900 truncate">
                        {v.title}
                      </div>
                      <div className="text-[11px] text-stone-500 truncate">
                        {v.hookText}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 shrink-0 text-xs">
                    {v.status === 'rendering' ? (
                      <div className="w-24">
                        <div className="w-full bg-stone-200 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-orange-500 h-full animate-pulse" style={{ width: `${v.progress}%` }} />
                        </div>
                        <span className="text-[10px] text-orange-600 font-mono mt-0.5 block text-right tabular-nums">{v.progress}%</span>
                      </div>
                    ) : v.status === 'ready' ? (
                      <span className="flex items-center text-[11px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        <Check className="w-3 h-3 mr-1 text-emerald-600" />
                        Xong
                      </span>
                    ) : (
                      <span className="text-[11px] text-amber-700 font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                        Chờ lượt
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* VIEW 2: AUTO-PILOT 5-STAGE PIPELINE */}
      {pipelineView === 'autopilot' && (
        <div className="bg-white border border-orange-200/80 rounded-2xl p-6 shadow-xs space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-orange-100 pb-4">
            <div>
              <h3 className="text-sm font-bold text-stone-900 flex items-center space-x-2">
                <span>Quy trình Tự Động Hóa 5 Bước (Crawl-to-Publish Pipeline)</span>
              </h3>
              <p className="text-xs text-stone-500 mt-0.5">
                Chạy hoàn toàn tự động từ quét xu hướng tới kịch bản, giọng đọc, ảnh sinh và render video
              </p>
            </div>

            <button
              onClick={handleRunAutoPilot}
              disabled={isAutoPilotRunning}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-xl font-bold text-xs shadow-xs transition-all active:scale-95"
            >
              {isAutoPilotRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Đang thực thi Auto-Pilot...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>🚀 Kích hoạt Toàn Bộ Quy Trình (1-Click Run)</span>
                </>
              )}
            </button>
          </div>

          {/* Stepper Timeline */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {pipelineSteps.map((st, i) => (
              <div 
                key={st.id}
                className={`p-4 rounded-xl border transition-all ${
                  st.status === 'completed'
                    ? 'bg-emerald-50/70 border-emerald-200 text-stone-800'
                    : st.status === 'in_progress'
                    ? 'bg-orange-50 border-orange-400 ring-2 ring-orange-500/20 text-stone-900 shadow-xs'
                    : 'bg-stone-50/80 border-stone-200 text-stone-500'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    st.status === 'completed'
                      ? 'bg-emerald-600 text-white'
                      : st.status === 'in_progress'
                      ? 'bg-orange-600 text-white animate-pulse'
                      : 'bg-stone-200 text-stone-600'
                  }`}>
                    {st.status === 'completed' ? <Check className="w-3.5 h-3.5" /> : i + 1}
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider">
                    {st.status === 'completed' && <span className="text-emerald-700">Hoàn thành</span>}
                    {st.status === 'in_progress' && <span className="text-orange-700 animate-pulse">Đang chạy</span>}
                    {st.status === 'queued' && <span className="text-stone-400">Chờ lệnh</span>}
                  </span>
                </div>
                <h4 className="font-bold text-xs text-stone-900 mb-1">{st.name}</h4>
                <p className="text-[11px] text-stone-600 leading-relaxed">{st.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 3: MULTI-PLATFORM AUTO-REFRAME */}
      {pipelineView === 'platforms' && (
        <div className="bg-white border border-orange-200/80 rounded-2xl p-6 shadow-xs space-y-6">
          <div className="border-b border-orange-100 pb-3">
            <h3 className="text-sm font-bold text-stone-900">
              Kiểm Tra Vùng An Toàn Đa Nền Tảng (Safe-Zone Validation)
            </h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Đảm bảo phụ đề chữ và hình ảnh chính không bị nút bấm UI của TikTok, YouTube Shorts, Reels che khuất
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* TikTok Preview Card */}
            <div className="border border-stone-200 rounded-xl p-4 bg-stone-50 space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-stone-800">
                <span>TikTok 9:16</span>
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Safe Margin: 20%
                </span>
              </div>
              <div className="relative aspect-[9/16] max-h-[320px] mx-auto bg-stone-900 rounded-lg overflow-hidden border border-stone-700">
                <ImageWithFallback
                  src={activePreviewVariant?.thumbnailUrl}
                  alt="TikTok Safe Zone"
                  className="w-full h-full object-cover opacity-80"
                />
                <div className="absolute right-2 bottom-12 flex flex-col space-y-3 text-white text-[10px] items-center">
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">❤️</span>
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">💬</span>
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">↗️</span>
                </div>
                <div className="absolute inset-x-3 bottom-4 text-center">
                  <span className="bg-amber-400 text-stone-900 text-[10px] font-black px-2 py-1 rounded shadow">
                    PHỤ ĐỀ NẰM VÙNG AN TOÀN
                  </span>
                </div>
              </div>
            </div>

            {/* YouTube Shorts Preview Card */}
            <div className="border border-stone-200 rounded-xl p-4 bg-stone-50 space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-stone-800">
                <span>YouTube Shorts 9:16</span>
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Top Header Safe
                </span>
              </div>
              <div className="relative aspect-[9/16] max-h-[320px] mx-auto bg-stone-900 rounded-lg overflow-hidden border border-stone-700">
                <ImageWithFallback
                  src={activePreviewVariant?.thumbnailUrl}
                  alt="Shorts Safe Zone"
                  className="w-full h-full object-cover opacity-80"
                />
                <div className="absolute left-2 bottom-3 right-12 text-white text-[10px]">
                  <div className="font-bold truncate">@channel_official · Đăng ký</div>
                  <div className="text-[9px] text-stone-300 truncate">Âm thanh gốc - Nhạc xu hướng</div>
                </div>
                <div className="absolute inset-x-3 top-1/2 text-center -translate-y-1/2">
                  <span className="bg-white text-stone-900 text-[10px] font-bold px-2 py-1 rounded shadow">
                    Hook chữ giữa khung hình
                  </span>
                </div>
              </div>
            </div>

            {/* Instagram Reels Preview Card */}
            <div className="border border-stone-200 rounded-xl p-4 bg-stone-50 space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-stone-800">
                <span>Instagram Reels 9:16</span>
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Ready to Publish
                </span>
              </div>
              <div className="relative aspect-[9/16] max-h-[320px] mx-auto bg-stone-900 rounded-lg overflow-hidden border border-stone-700">
                <ImageWithFallback
                  src={activePreviewVariant?.thumbnailUrl}
                  alt="Reels Safe Zone"
                  className="w-full h-full object-cover opacity-80"
                />
                <div className="absolute right-2 bottom-10 flex flex-col space-y-3 text-white text-[10px] items-center">
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">❤️</span>
                  <span className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">✈️</span>
                </div>
                <div className="absolute inset-x-3 bottom-6 text-center">
                  <span className="bg-orange-600 text-white text-[10px] font-bold px-2 py-1 rounded shadow">
                    Chuẩn kích thước 1080x1920
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
