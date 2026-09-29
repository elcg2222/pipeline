import React, { useState, useEffect } from 'react';
import { 
  Play, Pause, SkipBack, SkipForward, Scissors, 
  Download, Check, Film, Layers
} from 'lucide-react';
import { SceneItem, TimelineClip, SpeedCurveType, ResearchAsset } from '../types';
import { ImageWithFallback } from './ImageWithFallback';

interface MiniVideoEditorProps {
  scenes: SceneItem[];
  availableAssets: ResearchAsset[];
  projectName: string;
}

export const MiniVideoEditor: React.FC<MiniVideoEditorProps> = ({
  scenes,
  availableAssets,
  projectName
}) => {
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16'>('9:16');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [timelineZoom, setTimelineZoom] = useState(1);
  const [activePropertyTab, setActivePropertyTab] = useState<'speed' | 'cut' | 'broll'>('speed');

  const [selectedClipId, setSelectedClipId] = useState<string>('clip_main_1');
  const [selectedSpeedCurve, setSelectedSpeedCurve] = useState<SpeedCurveType>('hero');
  const [speedMultiplier, setSpeedMultiplier] = useState(1.2);
  const [trimIn, setTrimIn] = useState(0);
  const [trimOut, setTrimOut] = useState(10);

  const [tracks, setTracks] = useState<{
    main: TimelineClip[];
    broll: TimelineClip[];
    audio: TimelineClip[];
    captions: TimelineClip[];
  }>({
    main: [
      {
        id: 'clip_main_1',
        trackId: 'main',
        start: 0,
        duration: 8,
        title: scenes[0]?.visual_intent || 'Cảnh 1: Khung cảnh mở đầu',
        speedCurve: 'constant',
        color: '#ea580c',
        mediaUrl: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80'
      },
      {
        id: 'clip_main_2',
        trackId: 'main',
        start: 8,
        duration: 10,
        title: scenes[1]?.visual_intent || 'Cảnh 2: Chi tiết hành động',
        speedCurve: 'hero',
        color: '#c2410c',
        mediaUrl: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80'
      },
      {
        id: 'clip_main_3',
        trackId: 'main',
        start: 18,
        duration: 12,
        title: scenes[2]?.visual_intent || 'Cảnh 3: Kết luận & Kêu gọi',
        speedCurve: 'constant',
        color: '#9a3412',
        mediaUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80'
      }
    ],
    broll: [
      {
        id: 'clip_broll_1',
        trackId: 'broll',
        start: 4,
        duration: 5,
        title: 'B-Roll: Macro Chip 2nm Overlay',
        color: '#9333ea',
        mediaUrl: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80'
      }
    ],
    audio: [
      {
        id: 'clip_audio_1',
        trackId: 'audio',
        start: 0,
        duration: 30,
        title: 'Voiceover Gemini Flash TTS (Aoede - Tiếng Việt chuẩn)',
        color: '#10b981'
      }
    ],
    captions: [
      {
        id: 'clip_cap_1',
        trackId: 'captions',
        start: 0,
        duration: 8,
        title: 'Sub: ' + (scenes[0]?.narration.slice(0, 30) || 'Chào mừng các bạn...'),
        color: '#f59e0b'
      },
      {
        id: 'clip_cap_2',
        trackId: 'captions',
        start: 8,
        duration: 10,
        title: 'Sub: ' + (scenes[1]?.narration.slice(0, 30) || 'Tiếp theo là phân đoạn...'),
        color: '#d97706'
      }
    ]
  });

  const totalDuration = 30;
  const [exportedColab, setExportedColab] = useState(false);

  useEffect(() => {
    let anim: number;
    let last = performance.now();
    if (isPlaying) {
      const loop = (now: number) => {
        const delta = (now - last) / 1000;
        last = now;
        setCurrentTime((prev) => {
          const next = prev + delta;
          if (next >= totalDuration) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
        anim = requestAnimationFrame(loop);
      };
      anim = requestAnimationFrame(loop);
    }
    return () => cancelAnimationFrame(anim);
  }, [isPlaying]);

  const activeMainClip = tracks.main.find(
    c => currentTime >= c.start && currentTime < c.start + c.duration
  ) || tracks.main[0];

  const activeBrollClip = tracks.broll.find(
    c => currentTime >= c.start && currentTime < c.start + c.duration
  );

  const activeCaption = tracks.captions.find(
    c => currentTime >= c.start && currentTime < c.start + c.duration
  );

  const handleAddBroll = (asset: ResearchAsset) => {
    const newBroll: TimelineClip = {
      id: `clip_broll_${Date.now()}`,
      trackId: 'broll',
      start: currentTime,
      duration: 4,
      title: `B-Roll: ${asset.title.slice(0, 25)}...`,
      mediaUrl: asset.previewUrl,
      color: '#a855f7'
    };
    setTracks(prev => ({
      ...prev,
      broll: [...prev.broll, newBroll]
    }));
  };

  const handleSplitClip = () => {
    const current = tracks.main.find(c => currentTime > c.start && currentTime < c.start + c.duration);
    if (!current) return;

    const firstDuration = currentTime - current.start;
    const secondDuration = current.duration - firstDuration;

    const clip1: TimelineClip = { ...current, duration: firstDuration };
    const clip2: TimelineClip = {
      ...current,
      id: `clip_main_${Date.now()}`,
      start: currentTime,
      duration: secondDuration,
      title: `${current.title} (Part 2)`
    };

    setTracks(prev => ({
      ...prev,
      main: prev.main.map(c => c.id === current.id ? clip1 : c).concat(clip2)
    }));
  };

  const handleExportToColab = () => {
    setExportedColab(true);

    const colabBundle = {
      version: '2.0-colab-flow3',
      project_name: projectName || 'Social_Trend_Project',
      exported_at: new Date().toISOString(),
      aspect_ratio: aspectRatio,
      total_duration_sec: totalDuration,
      fps: 30,
      tracks: {
        main_video: tracks.main,
        b_roll: tracks.broll,
        voiceover_tts: tracks.audio,
        captions_srt: tracks.captions
      },
      speed_curves: {
        active_curve: selectedSpeedCurve,
        multiplier: speedMultiplier
      },
      colab_execution_command: `!python flow3_v0_7_relative_timeline_preview_PATCHED.py --project_bundle project_export.json --render_resolution 1080p`
    };

    const jsonStr = JSON.stringify(colabBundle, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `colab_timeline_export_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setTimeout(() => setExportedColab(false), 3000);
  };

  return (
    <div className="space-y-5">
      {/* Top Bar with Aspect Ratio & Export */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-orange-100 text-orange-600 flex items-center justify-center font-bold">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-stone-900">
                Mini Video Editor (CapCut Style Timeline)
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] bg-orange-50 text-orange-700 font-semibold border border-orange-200">
                Multi-track
              </span>
            </div>
            <p className="text-xs text-stone-500">
              Chỉnh sửa nhanh tốc độ, cắt ghép & B-Roll trước khi đẩy lên Kaggle / Colab GPU
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Aspect Ratio Switcher */}
          <div className="flex items-center bg-stone-100 p-1 rounded-xl border border-stone-200 text-xs">
            <button
              onClick={() => setAspectRatio('9:16')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                aspectRatio === '9:16' ? 'bg-white text-orange-700 shadow-xs font-bold' : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              9:16 (Shorts/TikTok)
            </button>
            <button
              onClick={() => setAspectRatio('16:9')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                aspectRatio === '16:9' ? 'bg-white text-orange-700 shadow-xs font-bold' : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              16:9 (YouTube)
            </button>
          </div>

          {/* Export to Colab Action */}
          <button
            onClick={handleExportToColab}
            className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-xs transition-all active:scale-95 ${
              exportedColab
                ? 'bg-emerald-600 text-white'
                : 'bg-orange-600 hover:bg-orange-700 text-white'
            }`}
          >
            {exportedColab ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Đã xuất file Colab JSON!</span>
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>📦 Export Project to Colab</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Top Center: Video Monitor + Right Properties Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* ================= VIDEO PREVIEW MONITOR (8 Cols) ================= */}
        <div className="lg:col-span-8 bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-col items-center justify-between shadow-xs">
          <div className="w-full flex items-center justify-between text-xs text-stone-500 mb-2 px-2">
            <span className="font-semibold text-stone-800">Preview Monitor (Khung Hình Xem Trước)</span>
            <span className="font-mono text-orange-600 font-bold tabular-nums">
              {currentTime.toFixed(2)}s / {totalDuration}.00s
            </span>
          </div>

          {/* Screen Canvas (16:9 or 9:16) */}
          <div
            className={`relative bg-stone-900 rounded-xl overflow-hidden border-2 border-stone-800 shadow-xl flex items-center justify-center transition-all ${
              aspectRatio === '16:9'
                ? 'w-full max-w-[560px] aspect-video'
                : 'w-[260px] aspect-[9/16]'
            }`}
          >
            {/* Main Video Layer */}
            <ImageWithFallback
              src={activeMainClip?.mediaUrl || 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80'}
              alt="Main preview"
              className="w-full h-full object-cover"
            />

            {/* B-Roll Picture-in-Picture Layer */}
            {activeBrollClip && (
              <div className="absolute top-4 right-4 w-32 aspect-video bg-black rounded-lg border-2 border-purple-500 overflow-hidden shadow-2xl animate-fade-in">
                <ImageWithFallback
                  src={activeBrollClip.mediaUrl}
                  alt="B-Roll Overlay"
                  className="w-full h-full object-cover"
                />
                <span className="absolute bottom-1 left-1 bg-black/80 text-[9px] font-bold text-purple-300 px-1 rounded">
                  B-ROLL
                </span>
              </div>
            )}

            {/* Soft Caption Overlay */}
            {activeCaption && (
              <div className="absolute bottom-5 inset-x-4 text-center pointer-events-none">
                <span className="inline-block bg-black/80 backdrop-blur-md text-amber-300 font-bold text-xs sm:text-sm px-3.5 py-1.5 rounded-lg border border-amber-400/40 shadow-lg">
                  {activeCaption.title.replace('Sub: ', '')}
                </span>
              </div>
            )}
          </div>

          {/* Player Transport Controls */}
          <div className="flex items-center justify-center space-x-3 w-full mt-4 pt-3 border-t border-stone-100">
            <button
              onClick={() => setCurrentTime(Math.max(0, currentTime - 2))}
              className="p-2 rounded-lg bg-stone-100 text-stone-700 hover:bg-stone-200"
              title="Lùi 2s"
            >
              <SkipBack className="w-4 h-4" />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-3 rounded-xl bg-orange-600 hover:bg-orange-700 text-white font-bold shadow-xs active:scale-95"
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-white" /> : <Play className="w-5 h-5 fill-white ml-0.5" />}
            </button>

            <button
              onClick={() => setCurrentTime(Math.min(totalDuration, currentTime + 2))}
              className="p-2 rounded-lg bg-stone-100 text-stone-700 hover:bg-stone-200"
              title="Tiến 2s"
            >
              <SkipForward className="w-4 h-4" />
            </button>

            <div className="h-5 w-px bg-stone-200 mx-2" />

            <button
              onClick={handleSplitClip}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200 text-xs font-semibold"
            >
              <Scissors className="w-3.5 h-3.5" />
              <span>Split tại kim đọc</span>
            </button>
          </div>
        </div>

        {/* ================= RIGHT PANEL: PROPERTIES (4 Cols) ================= */}
        <div className="lg:col-span-4 bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-col h-[480px] shadow-xs">
          {/* Tabs */}
          <div className="flex items-center space-x-1 bg-stone-100 p-1 rounded-xl border border-stone-200 mb-4">
            <button
              onClick={() => setActivePropertyTab('speed')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activePropertyTab === 'speed' ? 'bg-white text-orange-700 shadow-xs font-bold' : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Speed Curve
            </button>
            <button
              onClick={() => setActivePropertyTab('cut')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activePropertyTab === 'cut' ? 'bg-white text-orange-700 shadow-xs font-bold' : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Cut/Trim
            </button>
            <button
              onClick={() => setActivePropertyTab('broll')}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold text-center transition-all ${
                activePropertyTab === 'broll' ? 'bg-white text-orange-700 shadow-xs font-bold' : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              B-Roll Hub
            </button>
          </div>

          {/* TAB 1: SPEED CURVE */}
          {activePropertyTab === 'speed' && (
            <div className="space-y-4 flex-grow overflow-y-auto pr-1">
              <div className="text-xs font-semibold text-stone-800">Đường cong tốc độ (Speed Curve):</div>
              
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'constant', name: 'Đều đặn (1.0x)' },
                  { id: 'hero', name: 'Hero (Chậm ➔ Nhanh)' },
                  { id: 'montage', name: 'Montage (Nhịp điệu)' },
                  { id: 'bullet_time', name: 'Bullet-time (0.3x)' }
                ].map((sc) => (
                  <button
                    key={sc.id}
                    onClick={() => setSelectedSpeedCurve(sc.id as any)}
                    className={`p-2.5 rounded-xl border text-xs font-medium text-left transition-all ${
                      selectedSpeedCurve === sc.id
                        ? 'bg-orange-50 border-orange-500 text-orange-900 font-bold ring-1 ring-orange-500/20'
                        : 'bg-stone-50 border-stone-200 text-stone-600 hover:border-orange-300'
                    }`}
                  >
                    {sc.name}
                  </button>
                ))}
              </div>

              {/* Multiplier Slider */}
              <div className="pt-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-stone-600">Hệ số tốc độ:</span>
                  <span className="text-orange-600 font-mono font-bold tabular-nums">{speedMultiplier.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min={0.2}
                  max={3.0}
                  step={0.1}
                  value={speedMultiplier}
                  onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                />
              </div>

              <div className="bg-orange-50/60 p-3 rounded-xl border border-orange-200 text-[11px] text-stone-600 leading-relaxed">
                Đường cong <span className="text-stone-900 font-semibold">{selectedSpeedCurve}</span> áp dụng mượt mà không làm vỡ âm thanh lời bình.
              </div>
            </div>
          )}

          {/* TAB 2: CUT / SPLIT */}
          {activePropertyTab === 'cut' && (
            <div className="space-y-4 flex-grow overflow-y-auto pr-1">
              <div className="text-xs font-semibold text-stone-800">Cắt gọt phân đoạn (Trim In/Out):</div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-stone-600">Điểm đầu (Trim In):</span>
                    <span className="text-stone-900 font-mono tabular-nums">{trimIn}s</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={15}
                    value={trimIn}
                    onChange={(e) => setTrimIn(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-stone-600">Điểm cuối (Trim Out):</span>
                    <span className="text-stone-900 font-mono tabular-nums">{trimOut}s</span>
                  </div>
                  <input
                    type="range"
                    min={5}
                    max={30}
                    value={trimOut}
                    onChange={(e) => setTrimOut(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                  />
                </div>
              </div>

              <button
                onClick={handleSplitClip}
                className="w-full py-2.5 rounded-xl bg-orange-50 text-orange-700 border border-orange-200 text-xs font-semibold hover:bg-orange-100 flex items-center justify-center space-x-1.5"
              >
                <Scissors className="w-4 h-4" />
                <span>Cắt đôi clip tại vị trí {currentTime.toFixed(1)}s</span>
              </button>
            </div>
          )}

          {/* TAB 3: B-ROLL OVERLAY */}
          {activePropertyTab === 'broll' && (
            <div className="space-y-3 flex-grow overflow-y-auto pr-1">
              <div className="text-xs font-semibold text-stone-800">Kéo thả / Bấm để chèn B-Roll:</div>
              <div className="space-y-2">
                {availableAssets.slice(0, 4).map((ast) => (
                  <div
                    key={ast.id}
                    className="bg-stone-50 border border-stone-200 rounded-xl p-2 flex items-center justify-between hover:border-orange-300 transition-colors"
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <div className="w-10 h-8 rounded overflow-hidden shrink-0">
                        <ImageWithFallback src={ast.previewUrl} alt={ast.title} className="w-full h-full object-cover" />
                      </div>
                      <span className="text-[11px] text-stone-800 truncate max-w-[140px] font-medium">{ast.title}</span>
                    </div>
                    <button
                      onClick={() => handleAddBroll(ast)}
                      className="px-2 py-1 rounded bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200 text-[10px] font-bold"
                    >
                      + Chèn B-Roll
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>

      {/* ================= BOTTOM PANEL: MULTI-TRACK TIMELINE ================= */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-3">
        {/* Timeline Header Toolbar */}
        <div className="flex items-center justify-between border-b border-orange-100 pb-3 text-xs">
          <div className="flex items-center space-x-3">
            <span className="font-bold text-stone-800 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
              <Layers className="w-3.5 h-3.5 text-orange-600" />
              <span>Multi-track Timeline (CapCut Web Style)</span>
            </span>
            <span className="text-stone-500 font-mono tabular-nums">
              Kim đọc: {currentTime.toFixed(2)}s / {totalDuration}s
            </span>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-stone-500">Thu phóng:</span>
            <button
              onClick={() => setTimelineZoom(Math.max(0.7, timelineZoom - 0.2))}
              className="px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200 hover:bg-stone-200"
            >
              -
            </button>
            <span className="font-mono text-stone-800 text-[11px] tabular-nums">{(timelineZoom * 100).toFixed(0)}%</span>
            <button
              onClick={() => setTimelineZoom(Math.min(2.0, timelineZoom + 0.2))}
              className="px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stone-200 hover:bg-stone-200"
            >
              +
            </button>
          </div>
        </div>

        {/* Timeline Tracks Box */}
        <div className="relative bg-stone-50/80 border border-stone-200 rounded-xl p-3 overflow-x-auto min-h-[220px]">
          
          {/* Time Ruler */}
          <div className="flex items-center h-6 border-b border-stone-200 mb-2 text-[10px] font-mono text-stone-500">
            <div className="w-24 shrink-0 text-stone-600 font-semibold">Track</div>
            <div className="grow flex justify-between px-2">
              {[0, 5, 10, 15, 20, 25, 30].map(sec => (
                <span key={sec}>{sec}s</span>
              ))}
            </div>
          </div>

          {/* Orange Playhead line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-orange-600 z-20 pointer-events-none transition-all"
            style={{
              left: `calc(96px + ${(currentTime / totalDuration) * 85}%)`
            }}
          >
            <div className="w-2.5 h-2.5 bg-orange-600 -ml-1 rounded-full shadow-md" />
          </div>

          <div className="space-y-2">
            {/* TRACK 1: MAIN VIDEO */}
            <div className="flex items-center h-10">
              <div className="w-24 shrink-0 text-[11px] font-bold text-orange-700">
                🎬 Main Video
              </div>
              <div className="grow relative h-9 bg-stone-100 rounded-lg border border-stone-200 flex items-center overflow-hidden">
                {tracks.main.map((clip) => {
                  const widthPercent = (clip.duration / totalDuration) * 100;
                  const leftPercent = (clip.start / totalDuration) * 100;
                  const isSelected = selectedClipId === clip.id;
                  return (
                    <div
                      key={clip.id}
                      onClick={() => setSelectedClipId(clip.id)}
                      className={`absolute top-0.5 bottom-0.5 rounded px-2 flex items-center justify-between text-[11px] font-semibold text-white truncate cursor-pointer transition-all border ${
                        isSelected
                          ? 'border-amber-300 ring-2 ring-orange-500/50 z-10'
                          : 'border-orange-400/40 hover:brightness-110'
                      }`}
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                        backgroundColor: clip.color || '#ea580c'
                      }}
                    >
                      <span className="truncate">{clip.title}</span>
                      <span className="text-[9px] font-mono opacity-80 tabular-nums">{clip.duration}s</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* TRACK 2: B-ROLL */}
            <div className="flex items-center h-10">
              <div className="w-24 shrink-0 text-[11px] font-bold text-purple-700">
                🖼️ B-Roll / AI
              </div>
              <div className="grow relative h-9 bg-stone-100 rounded-lg border border-stone-200 flex items-center overflow-hidden">
                {tracks.broll.map((clip) => {
                  const widthPercent = (clip.duration / totalDuration) * 100;
                  const leftPercent = (clip.start / totalDuration) * 100;
                  return (
                    <div
                      key={clip.id}
                      className="absolute top-0.5 bottom-0.5 rounded px-2 flex items-center justify-between text-[11px] font-semibold text-white truncate cursor-pointer border border-purple-400/40"
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`,
                        backgroundColor: clip.color || '#9333ea'
                      }}
                    >
                      <span className="truncate">{clip.title}</span>
                      <span className="text-[9px] font-mono opacity-80 tabular-nums">{clip.duration}s</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* TRACK 3: VOICEOVER TTS */}
            <div className="flex items-center h-10">
              <div className="w-24 shrink-0 text-[11px] font-bold text-emerald-700">
                🎙️ Voiceover
              </div>
              <div className="grow relative h-9 bg-stone-100 rounded-lg border border-stone-200 flex items-center overflow-hidden">
                {tracks.audio.map((clip) => {
                  const widthPercent = (clip.duration / totalDuration) * 100;
                  const leftPercent = (clip.start / totalDuration) * 100;
                  return (
                    <div
                      key={clip.id}
                      className="absolute top-0.5 bottom-0.5 rounded px-2 flex items-center justify-between text-[11px] font-semibold text-white truncate border border-emerald-400/40 bg-emerald-600"
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`
                      }}
                    >
                      <span className="truncate">{clip.title}</span>
                      <span className="text-[9px] font-mono opacity-80">TTS 48kHz</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* TRACK 4: TEXT / CAPTIONS */}
            <div className="flex items-center h-10">
              <div className="w-24 shrink-0 text-[11px] font-bold text-amber-700">
                📝 Captions
              </div>
              <div className="grow relative h-9 bg-stone-100 rounded-lg border border-stone-200 flex items-center overflow-hidden">
                {tracks.captions.map((clip) => {
                  const widthPercent = (clip.duration / totalDuration) * 100;
                  const leftPercent = (clip.start / totalDuration) * 100;
                  return (
                    <div
                      key={clip.id}
                      className="absolute top-0.5 bottom-0.5 rounded px-2 flex items-center justify-between text-[10px] font-semibold text-white truncate border border-amber-400/40 bg-amber-600"
                      style={{
                        left: `${leftPercent}%`,
                        width: `${widthPercent}%`
                      }}
                    >
                      <span className="truncate">{clip.title}</span>
                      <span className="text-[9px] font-mono opacity-80 tabular-nums">{clip.duration}s</span>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};
