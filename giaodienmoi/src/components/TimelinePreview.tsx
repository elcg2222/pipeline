import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, 
  RotateCcw, Sparkles, Film, Subtitles, List, Edit3, 
  Plus, Trash2, Save, FileText, Check, Clock, ChevronRight
} from 'lucide-react';
import { ProjectDetail, ProjectSummary, SceneItem, SubtitleCue } from '../types';
import { parseSRT, cuesToSRT, secondsToTimestamp } from '../utils/srtParser';

interface TimelinePreviewProps {
  projects: ProjectSummary[];
  currentProject: ProjectDetail | null;
  onSelectProject: (id: string) => void;
  onCreateProject: (title: string, aspectRatio: '9:16' | '16:9' | '1:1', script: string) => Promise<void>;
  onUpdateProject: (id: string, data: any) => Promise<void>;
  isLoading: boolean;
}

export const TimelinePreview: React.FC<TimelinePreviewProps> = ({
  projects,
  currentProject,
  onSelectProject,
  onCreateProject,
  onUpdateProject,
  isLoading
}) => {
  // Player state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [showSoftSubtitles, setShowSoftSubtitles] = useState(true);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Tabs on right panel
  const [rightTab, setRightTab] = useState<'scenes' | 'subtitles' | 'script'>('scenes');
  const [rawSRT, setRawSRT] = useState('');
  const [isRawSRTMode, setIsRawSRTMode] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  // New project modal state
  const [showNewModal, setShowNewModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newRatio, setNewRatio] = useState<'9:16' | '16:9' | '1:1'>('9:16');
  const [newScript, setNewScript] = useState('');

  // Editing active scene
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [localScenes, setLocalScenes] = useState<SceneItem[]>([]);

  // Subtitles
  const [cues, setCues] = useState<SubtitleCue[]>([]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);

  // Initialize or update local state when currentProject changes
  useEffect(() => {
    if (currentProject) {
      setLocalScenes(currentProject.scenes || []);
      const parsed = parseSRT(currentProject.subtitles || '');
      setCues(parsed);
      setRawSRT(currentProject.subtitles || '');
      setCurrentTime(0);
      setIsPlaying(false);
      setActiveSceneIndex(0);
    }
  }, [currentProject]);

  // Calculate total project duration from scenes
  const totalDuration = localScenes.reduce(
    (sum, s) => sum + (Number(s.estimated_duration_sec) || 5), 
    0
  ) || 45;

  // Find active scene based on currentTime
  useEffect(() => {
    let accumulated = 0;
    for (let i = 0; i < localScenes.length; i++) {
      const dur = Number(localScenes[i].estimated_duration_sec) || 5;
      if (currentTime >= accumulated && currentTime < accumulated + dur) {
        setActiveSceneIndex(i);
        return;
      }
      accumulated += dur;
    }
    if (localScenes.length > 0 && currentTime >= totalDuration) {
      setActiveSceneIndex(localScenes.length - 1);
    }
  }, [currentTime, localScenes, totalDuration]);

  // Playback timer loop
  useEffect(() => {
    if (isPlaying) {
      lastTimeRef.current = performance.now();
      const step = (now: number) => {
        const delta = (now - lastTimeRef.current) / 1000;
        lastTimeRef.current = now;

        setCurrentTime((prev) => {
          const next = prev + delta;
          if (next >= totalDuration) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });

        animationFrameRef.current = requestAnimationFrame(step);
      };
      animationFrameRef.current = requestAnimationFrame(step);
    } else {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, totalDuration]);

  // Handle scene audio sync
  const currentScene = localScenes[activeSceneIndex];

  useEffect(() => {
    if (currentProject && currentScene?.audio && audioRef.current) {
      const audioUrl = `/api/asset/${currentProject.id}/${currentScene.audio}`;
      if (audioRef.current.src !== window.location.origin + audioUrl) {
        audioRef.current.src = audioUrl;
      }
      if (isPlaying) {
        audioRef.current.play().catch(() => {});
      } else {
        audioRef.current.pause();
      }
    }
  }, [activeSceneIndex, isPlaying, currentProject, currentScene]);

  // Find active subtitle cue
  const activeCue = cues.find(c => currentTime >= c.start && currentTime <= c.end);

  // Jump to specific scene
  const jumpToScene = (idx: number) => {
    let startSec = 0;
    for (let i = 0; i < idx; i++) {
      startSec += Number(localScenes[i].estimated_duration_sec) || 5;
    }
    setCurrentTime(startSec);
    setActiveSceneIndex(idx);
  };

  // Jump to cue timestamp
  const seekToCue = (cue: SubtitleCue) => {
    setCurrentTime(cue.start);
    if (!isPlaying) setIsPlaying(true);
  };

  // Save changes
  const handleSaveProject = async () => {
    if (!currentProject) return;
    const finalSRT = isRawSRTMode ? rawSRT : cuesToSRT(cues);
    await onUpdateProject(currentProject.id, {
      scenes: localScenes,
      subtitles: finalSRT
    });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  // Add scene
  const handleAddScene = () => {
    const newScene: SceneItem = {
      scene_id: `scene_${String(localScenes.length + 1).padStart(3, '0')}`,
      chapter_id: `Cảnh ${localScenes.length + 1}`,
      narration: 'Lời bình thuyết minh cho cảnh mới...',
      estimated_duration_sec: 10,
      visual_intent: `Cảnh ${localScenes.length + 1}: Diễn biến mới`,
      status: 'ready',
      format: currentProject?.brief.aspect_ratio || '9:16',
      tts_profile: 'male_warm'
    };
    setLocalScenes([...localScenes, newScene]);
  };

  // Remove scene
  const handleRemoveScene = (idx: number) => {
    if (localScenes.length <= 1) {
      alert('Dự án cần có ít nhất 1 cảnh.');
      return;
    }
    const updated = localScenes.filter((_, i) => i !== idx);
    setLocalScenes(updated);
    if (activeSceneIndex >= updated.length) {
      setActiveSceneIndex(updated.length - 1);
    }
  };

  // Update scene field
  const updateScene = (idx: number, field: keyof SceneItem, val: any) => {
    const updated = [...localScenes];
    updated[idx] = { ...updated[idx], [field]: val };
    setLocalScenes(updated);
  };

  const handleCreateNew = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await onCreateProject(newTitle, newRatio, newScript);
    setShowNewModal(false);
    setNewTitle('');
    setNewScript('');
  };

  const aspectRatio = currentProject?.brief.aspect_ratio || '9:16';

  return (
    <div className="space-y-6">
      {/* Hidden Audio element for narration sync */}
      <audio 
        ref={audioRef} 
        onEnded={() => {
          if (activeSceneIndex < localScenes.length - 1) {
            jumpToScene(activeSceneIndex + 1);
          }
        }}
      />

      {/* Top Bar: Project Selector & Quick Info */}
      <div className="bg-[#171a23] border border-[#262b38] rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-semibold text-[#8b90a0]">Dự án đang mở:</label>
          <select
            value={currentProject?.id || ''}
            onChange={(e) => onSelectProject(e.target.value)}
            className="bg-[#10131b] border border-[#262b38] text-white text-xs rounded-xl px-3 py-2 font-medium focus:outline-none focus:border-blue-500 min-w-[280px]"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} ({p.aspectRatio} · {p.scenesCount} cảnh · {Math.round(p.duration)}s)
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 text-xs font-semibold transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Tạo dự án mới</span>
          </button>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-xs text-[#8b90a0] flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded bg-[#10131b] border border-[#262b38] text-white font-mono">
              Tỉ lệ: {aspectRatio}
            </span>
            <span className="px-2 py-0.5 rounded bg-[#10131b] border border-[#262b38] text-white font-mono">
              30 FPS
            </span>
          </div>

          <button
            onClick={handleSaveProject}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-colors"
          >
            {isSaved ? (
              <>
                <Check className="w-3.5 h-3.5 text-white" />
                <span>Đã lưu thành công</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Lưu thay đổi</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Studio Layout: Player (Left) + Editor Tabs (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Visual Preview Canvas & Timeline Player (5 cols) */}
        <div className="lg:col-span-5 flex flex-col items-center">
          <div className="bg-[#171a23] border border-[#262b38] rounded-2xl p-4 w-full shadow-sm flex flex-col items-center">
            
            {/* Aspect Ratio Canvas Container */}
            <div 
              className={`relative bg-[#0a0c12] border-2 border-[#2b3345] rounded-xl overflow-hidden shadow-2xl flex items-center justify-center transition-all ${
                aspectRatio === '9:16'
                  ? 'w-[280px] h-[498px]'
                  : aspectRatio === '16:9'
                  ? 'w-[420px] h-[236px]'
                  : 'w-[320px] h-[320px]'
              }`}
            >
              {/* Media Asset or Visual Intent Mockup */}
              {currentProject && currentScene?.media ? (
                <img
                  src={`/api/asset/${currentProject.id}/${currentScene.media}`}
                  alt="Scene Visual"
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to stylized poster if media image fails
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              ) : null}

              {/* Dynamic Overlay Graphic Backdrop if no image or during transition */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-black/60 flex flex-col justify-between p-4 pointer-events-none">
                {/* Top Scene Chapter Badge */}
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-600/80 text-white backdrop-blur-sm uppercase tracking-wide">
                    {currentScene?.scene_id || 'Cảnh 1'}
                  </span>
                  <span className="text-[10px] text-white/80 font-mono bg-black/40 px-2 py-0.5 rounded backdrop-blur-sm">
                    {Math.round(currentTime)}s / {Math.round(totalDuration)}s
                  </span>
                </div>

                {/* Center Visual Intent Text */}
                <div className="text-center px-3">
                  <h4 className="text-xs font-semibold text-white/90 drop-shadow-md">
                    {currentScene?.visual_intent || 'Cảnh quay minh hoạ'}
                  </h4>
                </div>

                {/* Soft Subtitles (Phụ đề mềm trên Canvas) */}
                {showSoftSubtitles && (
                  <div className="w-full text-center pb-2 px-2 transition-all">
                    {activeCue ? (
                      <div className="inline-block bg-black/75 backdrop-blur-sm text-yellow-300 font-bold text-xs sm:text-sm px-3 py-1.5 rounded-lg border border-yellow-400/30 shadow-lg leading-snug">
                        {activeCue.text}
                      </div>
                    ) : (
                      <div className="h-6" />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Subtitle Soft Toggle */}
            <div className="w-full flex items-center justify-between text-xs text-[#8b90a0] mt-3 px-2">
              <label className="flex items-center space-x-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={showSoftSubtitles}
                  onChange={(e) => setShowSoftSubtitles(e.target.checked)}
                  className="rounded border-[#262b38] text-blue-600 focus:ring-0 bg-[#10131b]"
                />
                <span className="text-white font-medium">Bật phụ đề mềm (Soft Subs)</span>
              </label>
              <span className="text-[11px] text-emerald-400">
                {activeCue ? `Cue #${activeCue.id}` : 'Đồng bộ thời gian'}
              </span>
            </div>

            {/* Timeline Scrubber */}
            <div className="w-full mt-4 space-y-2 px-2">
              <div className="flex items-center justify-between text-xs font-mono text-[#8b90a0]">
                <span>{secondsToTimestamp(currentTime)}</span>
                <span>{secondsToTimestamp(totalDuration)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={totalDuration}
                step={0.1}
                value={currentTime}
                onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            {/* Playback Controls */}
            <div className="flex items-center justify-between w-full mt-3 px-4 pt-2 border-t border-[#262b38]">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className="p-2 rounded-lg bg-[#202633] text-white hover:bg-[#2b3345] transition-colors"
                >
                  {isMuted ? <VolumeX className="w-4 h-4 text-rose-400" /> : <Volume2 className="w-4 h-4 text-[#8b90a0]" />}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value))}
                  className="w-16 h-1 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    if (activeSceneIndex > 0) jumpToScene(activeSceneIndex - 1);
                  }}
                  disabled={activeSceneIndex === 0}
                  className="p-2 rounded-lg bg-[#202633] text-white hover:bg-[#2b3345] transition-colors disabled:opacity-40"
                  title="Cảnh trước"
                >
                  <SkipBack className="w-4 h-4" />
                </button>

                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="p-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold transition-all shadow-md"
                  title={isPlaying ? 'Tạm dừng' : 'Phát'}
                >
                  {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                </button>

                <button
                  onClick={() => {
                    if (activeSceneIndex < localScenes.length - 1) jumpToScene(activeSceneIndex + 1);
                  }}
                  disabled={activeSceneIndex >= localScenes.length - 1}
                  className="p-2 rounded-lg bg-[#202633] text-white hover:bg-[#2b3345] transition-colors disabled:opacity-40"
                  title="Cảnh tiếp"
                >
                  <SkipForward className="w-4 h-4" />
                </button>
              </div>

              <button
                onClick={() => {
                  setCurrentTime(0);
                  setIsPlaying(false);
                }}
                className="p-2 rounded-lg bg-[#202633] text-[#8b90a0] hover:text-white hover:bg-[#2b3345] transition-colors"
                title="Về đầu"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

          </div>
        </div>

        {/* Right Column: Scenes & Subtitles Editor (7 cols) */}
        <div className="lg:col-span-7 bg-[#171a23] border border-[#262b38] rounded-2xl p-5 shadow-sm flex flex-col h-full">
          {/* Sub Navigation */}
          <div className="flex items-center justify-between border-b border-[#262b38] pb-3 mb-4">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setRightTab('scenes')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  rightTab === 'scenes'
                    ? 'bg-blue-600 text-white'
                    : 'text-[#8b90a0] hover:text-white hover:bg-[#202633]'
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>Danh sách cảnh ({localScenes.length})</span>
              </button>

              <button
                onClick={() => setRightTab('subtitles')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  rightTab === 'subtitles'
                    ? 'bg-blue-600 text-white'
                    : 'text-[#8b90a0] hover:text-white hover:bg-[#202633]'
                }`}
              >
                <Subtitles className="w-3.5 h-3.5" />
                <span>Phụ đề SRT ({cues.length})</span>
              </button>

              <button
                onClick={() => setRightTab('script')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  rightTab === 'script'
                    ? 'bg-blue-600 text-white'
                    : 'text-[#8b90a0] hover:text-white hover:bg-[#202633]'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Kịch bản gốc</span>
              </button>
            </div>

            {rightTab === 'scenes' && (
              <button
                onClick={handleAddScene}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[#202633] text-xs font-medium text-blue-400 hover:bg-[#2b3345] transition-colors"
              >
                <Plus className="w-3 h-3" />
                <span>Thêm cảnh</span>
              </button>
            )}
          </div>

          {/* TAB 1: SCENES LIST & EDITOR */}
          {rightTab === 'scenes' && (
            <div className="space-y-4 overflow-y-auto max-h-[560px] pr-2">
              {localScenes.map((scene, idx) => (
                <div
                  key={scene.scene_id || idx}
                  onClick={() => jumpToScene(idx)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    activeSceneIndex === idx
                      ? 'bg-[#1e2533] border-blue-500 shadow-md ring-1 ring-blue-500/20'
                      : 'bg-[#10131b] border-[#262b38] hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="w-6 h-6 rounded-full bg-blue-600/30 text-blue-400 font-bold text-xs flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <span className="text-xs font-bold text-white">
                        {scene.visual_intent || `Cảnh ${idx + 1}`}
                      </span>
                      {activeSceneIndex === idx && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          Đang xem
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 text-xs">
                      <div className="flex items-center space-x-1 text-[#8b90a0]">
                        <Clock className="w-3 h-3" />
                        <input
                          type="number"
                          min={1}
                          max={60}
                          value={scene.estimated_duration_sec || 10}
                          onChange={(e) => {
                            e.stopPropagation();
                            updateScene(idx, 'estimated_duration_sec', parseFloat(e.target.value) || 5);
                          }}
                          className="w-14 bg-[#171a23] border border-[#262b38] rounded px-1.5 py-0.5 text-white font-mono text-center focus:outline-none"
                        />
                        <span>giây</span>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveScene(idx);
                        }}
                        className="text-[#8b90a0] hover:text-rose-400 p-1"
                        title="Xóa cảnh"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Narration Edit */}
                  <div className="mt-2">
                    <label className="text-[11px] text-[#8b90a0] font-medium block mb-1">
                      Lời thuyết minh (Narration):
                    </label>
                    <textarea
                      rows={2}
                      value={scene.narration}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => updateScene(idx, 'narration', e.target.value)}
                      className="w-full bg-[#171a23] border border-[#262b38] rounded-lg p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  {/* Extra metadata */}
                  <div className="flex flex-wrap items-center justify-between gap-2 mt-2 pt-2 border-t border-[#262b38]/60 text-[11px] text-[#8b90a0]">
                    <div className="flex items-center space-x-2">
                      <span>Hiệu ứng:</span>
                      <select
                        value={scene.text_effect || 'fade'}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => updateScene(idx, 'text_effect', e.target.value)}
                        className="bg-[#171a23] border border-[#262b38] text-white rounded px-2 py-0.5"
                      >
                        <option value="fade">Fade in</option>
                        <option value="zoom_in">Zoom in</option>
                        <option value="pan_right">Pan right</option>
                        <option value="slide_up">Slide up</option>
                      </select>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span>TTS Voice:</span>
                      <span className="text-white font-mono bg-[#171a23] px-2 py-0.5 rounded border border-[#262b38]">
                        {scene.tts_profile || 'male_warm'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 2: SUBTITLES SRT SYNC & EDITOR */}
          {rightTab === 'subtitles' && (
            <div className="flex flex-col h-full space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#8b90a0]">
                  Bấm vào từng câu để tua đến đúng thời điểm (Seek).
                </span>
                <button
                  onClick={() => setIsRawSRTMode(!isRawSRTMode)}
                  className="text-blue-400 hover:underline"
                >
                  {isRawSRTMode ? 'Xem dạng bảng Cues' : 'Sửa file SRT thô'}
                </button>
              </div>

              {isRawSRTMode ? (
                <textarea
                  value={rawSRT}
                  onChange={(e) => {
                    setRawSRT(e.target.value);
                    setCues(parseSRT(e.target.value));
                  }}
                  className="w-full flex-grow h-96 bg-[#10131b] border border-[#262b38] rounded-xl p-3 text-xs font-mono text-emerald-400 focus:outline-none focus:border-blue-500"
                />
              ) : (
                <div className="space-y-2 overflow-y-auto max-h-[500px] pr-2">
                  {cues.length === 0 ? (
                    <div className="text-center py-12 text-[#8b90a0] text-xs">
                      Chưa có phụ đề SRT cho dự án này.
                    </div>
                  ) : (
                    cues.map((cue) => {
                      const isActive = currentTime >= cue.start && currentTime <= cue.end;
                      return (
                        <div
                          key={cue.id}
                          onClick={() => seekToCue(cue)}
                          className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                            isActive
                              ? 'bg-blue-600/20 border-blue-500 text-white font-medium ring-1 ring-blue-500/30'
                              : 'bg-[#10131b] border-[#262b38] text-[#e6e8ee] hover:border-gray-600'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[11px] text-[#8b90a0] mb-1 font-mono">
                            <span className="font-bold text-blue-400">#{cue.id}</span>
                            <span>{cue.startStr} ➔ {cue.endStr}</span>
                          </div>
                          <p className="leading-relaxed">{cue.text}</p>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: ORIGINAL SCRIPT */}
          {rightTab === 'script' && (
            <div className="space-y-3">
              <label className="text-xs text-[#8b90a0]">Kịch bản toàn văn dự án (script.md):</label>
              <textarea
                rows={14}
                value={currentProject?.script || ''}
                readOnly
                className="w-full bg-[#10131b] border border-[#262b38] rounded-xl p-3 text-xs font-mono text-white focus:outline-none"
              />
            </div>
          )}

        </div>
      </div>

      {/* Modal: Create New Project */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#171a23] border border-[#262b38] rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Film className="w-5 h-5 text-blue-500" />
              <span>Tạo dự án video mới</span>
            </h3>

            <form onSubmit={handleCreateNew} className="space-y-4">
              <div>
                <label className="text-xs text-[#8b90a0] block mb-1">Tên dự án:</label>
                <input
                  type="text"
                  required
                  placeholder="Ví dụ: Video Tin tức Công nghệ AI 2026"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-[#10131b] border border-[#262b38] rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-[#8b90a0] block mb-1">Tỉ lệ khung hình (Aspect Ratio):</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['9:16', '16:9', '1:1'] as const).map((ratio) => (
                    <button
                      type="button"
                      key={ratio}
                      onClick={() => setNewRatio(ratio)}
                      className={`py-2 text-xs font-semibold rounded-xl border transition-all ${
                        newRatio === ratio
                          ? 'bg-blue-600 text-white border-blue-500'
                          : 'bg-[#10131b] text-[#8b90a0] border-[#262b38] hover:text-white'
                      }`}
                    >
                      {ratio} {ratio === '9:16' ? '(Shorts/TikTok)' : ratio === '16:9' ? '(YouTube)' : '(Square)'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-[#8b90a0] block mb-1">Kịch bản mở đầu (tuỳ chọn):</label>
                <textarea
                  rows={4}
                  placeholder="Nhập nội dung kịch bản..."
                  value={newScript}
                  onChange={(e) => setNewScript(e.target.value)}
                  className="w-full bg-[#10131b] border border-[#262b38] rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-[#262b38]">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2 rounded-xl bg-[#202633] text-xs font-semibold text-[#8b90a0] hover:text-white"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white shadow-md"
                >
                  Tạo dự án
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
