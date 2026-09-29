import React, { useState } from 'react';
import { 
  FileText, Sparkles, Plus, Trash2, 
  Layers, Check, Wand2, Sliders, Image, Zap
} from 'lucide-react';
import { SceneItem } from '../types';
import { ImageWithFallback } from './ImageWithFallback';

interface ScriptStoryboardWorkspaceProps {
  scenes: SceneItem[];
  onUpdateScenes: (scenes: SceneItem[]) => void;
  onSendBatchToAgent: (scenes: SceneItem[]) => void;
  aspectRatio: string;
}

export const ScriptStoryboardWorkspace: React.FC<ScriptStoryboardWorkspaceProps> = ({
  scenes,
  onUpdateScenes,
  onSendBatchToAgent,
  aspectRatio
}) => {
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);
  const [aiPrompt, setAiPrompt] = useState('');
  const [isAiRewriting, setIsAiRewriting] = useState(false);
  const [batchSent, setBatchSent] = useState(false);

  const currentScene = scenes[activeSceneIndex] || scenes[0];

  const handleUpdateSceneField = (index: number, field: keyof SceneItem, value: any) => {
    const updated = [...scenes];
    updated[index] = { ...updated[index], [field]: value };
    onUpdateScenes(updated);
  };

  const handleAddSceneBlock = () => {
    const newIdx = scenes.length + 1;
    const newScene: SceneItem = {
      scene_id: `scene_${String(newIdx).padStart(3, '0')}`,
      chapter_id: `Phân đoạn ${newIdx}`,
      narration: 'Nội dung lời bình mới cho cảnh quay...',
      estimated_duration_sec: 10,
      visual_intent: `Cảnh ${newIdx}: Khung hình sinh động`,
      status: 'draft',
      format: aspectRatio || '9:16',
      tts_profile: 'male_warm',
      text_effect: 'fade',
      framing: 'Medium Shot'
    };
    onUpdateScenes([...scenes, newScene]);
    setActiveSceneIndex(scenes.length);
  };

  const handleDeleteScene = (index: number) => {
    if (scenes.length <= 1) {
      alert('Kịch bản cần có ít nhất một cảnh.');
      return;
    }
    const updated = scenes.filter((_, i) => i !== index);
    onUpdateScenes(updated);
    if (activeSceneIndex >= updated.length) {
      setActiveSceneIndex(updated.length - 1);
    }
  };

  const handleAiRewrite = (actionType?: string) => {
    if (!currentScene) return;
    setIsAiRewriting(true);
    
    setTimeout(() => {
      let rewritten = '';
      if (actionType === 'funny' || aiPrompt.toLowerCase().includes('hài hước')) {
        rewritten = `[Hài hước] ${currentScene.narration} Cứ ngỡ là đùa, ai dè công nghệ làm thật khiến ai cũng phải bật ngửa!`;
      } else if (actionType === 'hook' || aiPrompt.toLowerCase().includes('hook')) {
        rewritten = `DỪNG LẠI 3 GIÂY! Bạn sẽ không thể tin được: ${currentScene.narration}`;
      } else if (actionType === 'shorten' || aiPrompt.toLowerCase().includes('rút ngắn')) {
        const words = currentScene.narration.split(' ');
        rewritten = words.slice(0, Math.min(15, words.length)).join(' ') + '...';
      } else {
        rewritten = `[AI Tối ưu] ${currentScene.narration} - Mang lại cảm giác điện ảnh và kịch tính hơn cho phân cảnh.`;
      }

      handleUpdateSceneField(activeSceneIndex, 'narration', rewritten);
      setIsAiRewriting(false);
      setAiPrompt('');
    }, 500);
  };

  const handleSendBatch = () => {
    setBatchSent(true);
    onSendBatchToAgent(scenes);
    setTimeout(() => setBatchSent(false), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Action */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-xs">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-orange-100 text-orange-600 flex items-center justify-center font-bold">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-stone-900">
              Script & Storyboard Workspace (Kịch bản & Khung hình)
            </h2>
            <div className="text-xs text-stone-500 flex items-center space-x-1.5">
              <span>Soạn thảo dạng Block</span>
              <span aria-hidden="true">·</span>
              <span>Tự động map text sang Storyboard</span>
              <span aria-hidden="true">·</span>
              <span className="text-orange-600 font-medium">Đồng bộ Local Agent GPU</span>
            </div>
          </div>
        </div>

        {/* Highlight Batch Action Button */}
        <button
          onClick={handleSendBatch}
          disabled={batchSent}
          className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-md transition-all active:scale-95 ${
            batchSent
              ? 'bg-emerald-600 text-white shadow-emerald-500/20'
              : 'bg-gradient-to-r from-orange-500 via-orange-600 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white shadow-orange-500/20'
          }`}
        >
          {batchSent ? (
            <>
              <Check className="w-4 h-4 text-white" />
              <span>Đã chuyển vào Hàng Đợi Agent!</span>
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 text-amber-200 animate-pulse" />
              <span>Gửi toàn bộ sang Local Agent để Tạo Hàng Loạt</span>
            </>
          )}
        </button>
      </div>

      {/* 3-Column Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* ================= LEFT PANEL: SCRIPT EDITOR (4 Cols) ================= */}
        <div className="lg:col-span-4 bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-col h-[740px] shadow-xs">
          <div className="flex items-center justify-between border-b border-orange-100 pb-3 mb-3">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-orange-600" />
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                Block Script Editor ({scenes.length} cảnh)
              </h3>
            </div>
            <button
              onClick={handleAddSceneBlock}
              className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Thêm Block</span>
            </button>
          </div>

          {/* Block list */}
          <div className="flex-grow overflow-y-auto space-y-2.5 pr-1">
            {scenes.map((scene, idx) => {
              const isSelected = activeSceneIndex === idx;
              return (
                <div
                  key={scene.scene_id || idx}
                  onClick={() => setActiveSceneIndex(idx)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-orange-50/60 border-orange-400 shadow-xs ring-1 ring-orange-500/20'
                      : 'bg-stone-50/60 border-stone-200/80 hover:border-orange-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold flex items-center space-x-1.5">
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isSelected ? 'bg-orange-500 text-white' : 'bg-stone-200 text-stone-700'
                      }`}>
                        {idx + 1}
                      </span>
                      <span className="text-stone-900 font-semibold">{scene.scene_id}</span>
                    </span>

                    <div className="flex items-center space-x-2 text-[11px] text-stone-500">
                      <span className="font-mono bg-white px-1.5 py-0.5 rounded border border-stone-200 tabular-nums">
                        {scene.estimated_duration_sec}s
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteScene(idx);
                        }}
                        className="hover:text-red-500 p-0.5 text-stone-400"
                        title="Xóa block"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-stone-700 line-clamp-2 leading-relaxed">
                    {scene.narration}
                  </p>

                  <div className="mt-2 pt-2 border-t border-stone-200/60 flex items-center justify-between text-[10px] text-stone-500">
                    <span className="truncate max-w-[150px]">{scene.visual_intent}</span>
                    <span className="text-emerald-700 font-semibold uppercase">{scene.status || 'ready'}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* AI Script Agent Chat Inline Box */}
          <div className="pt-3 border-t border-orange-100 mt-2 space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-orange-700 flex items-center space-x-1">
                <Wand2 className="w-3.5 h-3.5 text-orange-600" />
                <span>AI Rewrite Cảnh {activeSceneIndex + 1}</span>
              </span>
            </div>

            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => handleAiRewrite('funny')}
                className="text-[10px] px-2 py-0.5 rounded bg-orange-50 text-orange-800 border border-orange-200 hover:bg-orange-100"
              >
                🤣 Viết hài hước
              </button>
              <button
                onClick={() => handleAiRewrite('hook')}
                className="text-[10px] px-2 py-0.5 rounded bg-orange-50 text-orange-800 border border-orange-200 hover:bg-orange-100"
              >
                🔥 Thêm Hook
              </button>
              <button
                onClick={() => handleAiRewrite('shorten')}
                className="text-[10px] px-2 py-0.5 rounded bg-orange-50 text-orange-800 border border-orange-200 hover:bg-orange-100"
              >
                ⚡ Rút gọn
              </button>
            </div>

            <div className="flex items-center space-x-1.5">
              <input
                type="text"
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAiRewrite()}
                placeholder="Yêu cầu AI viết lại nội dung..."
                className="w-full bg-stone-50 border border-orange-200 rounded-xl px-2.5 py-1.5 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
              />
              <button
                onClick={() => handleAiRewrite()}
                disabled={isAiRewriting || !aiPrompt.trim()}
                className="p-2 rounded-xl bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-40 transition-colors shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* ================= CENTER PANEL: VISUAL STORYBOARD (5 Cols) ================= */}
        <div className="lg:col-span-5 bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-col h-[740px] shadow-xs">
          <div className="flex items-center justify-between border-b border-orange-100 pb-3 mb-3">
            <div className="flex items-center space-x-2">
              <Image className="w-4 h-4 text-orange-600" />
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                Visual Storyboard (Khung hình ánh xạ)
              </h3>
            </div>
            <span className="text-[11px] text-stone-500 font-mono">
              Tỉ lệ: {aspectRatio || '9:16'}
            </span>
          </div>

          {/* Large Frame Preview */}
          <div className="flex flex-col items-center justify-center p-3 bg-stone-50 rounded-2xl border border-stone-200/80 mb-3">
            <div className="relative w-full max-w-[340px] aspect-[9/16] max-h-[380px] bg-stone-900 rounded-xl overflow-hidden border border-stone-800 shadow-xl flex items-center justify-center">
              {currentScene?.media ? (
                <ImageWithFallback
                  src={currentScene.media.startsWith('http') ? currentScene.media : `/api/asset/${currentScene.scene_id}/${currentScene.media}`}
                  alt={currentScene.visual_intent || 'Storyboard preview'}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center p-6 space-y-2">
                  <Image className="w-12 h-12 text-stone-700 mx-auto animate-pulse" />
                  <div className="text-xs font-semibold text-stone-300">
                    Ảnh tạo bởi Local Agent
                  </div>
                  <div className="text-[11px] text-stone-500">
                    Sẵn sàng batch generate
                  </div>
                </div>
              )}

              {/* Storyboard Soft Overlay Text */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/40 flex flex-col justify-between p-3 pointer-events-none">
                <div className="flex items-center justify-between">
                  <span className="bg-orange-600/90 text-white font-bold text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider">
                    {currentScene?.scene_id}
                  </span>
                  <span className="bg-black/60 text-white font-mono text-[10px] px-2 py-0.5 rounded tabular-nums">
                    {currentScene?.estimated_duration_sec}s
                  </span>
                </div>

                <div className="text-center px-2">
                  <div className="inline-block bg-black/80 backdrop-blur-md text-amber-300 font-bold text-xs px-3 py-1 rounded-lg border border-amber-400/40">
                    {currentScene?.narration || 'Lời bình hiển thị tại đây'}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-2 text-center text-xs font-semibold text-stone-800">
              {currentScene?.visual_intent || 'Ý đồ hình ảnh'}
            </div>
          </div>

          {/* Quick Scene Scroller */}
          <div className="flex-grow overflow-x-auto flex items-center space-x-2 pt-2 border-t border-stone-100">
            {scenes.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setActiveSceneIndex(idx)}
                className={`shrink-0 w-24 h-24 rounded-xl border p-2 flex flex-col justify-between text-left transition-all ${
                  activeSceneIndex === idx
                    ? 'bg-orange-50 border-orange-500 ring-2 ring-orange-500/20'
                    : 'bg-stone-50 border-stone-200 hover:border-stone-400'
                }`}
              >
                <div className="flex items-center justify-between text-[10px] font-bold">
                  <span className="text-orange-600">#{idx + 1}</span>
                  <span className="text-stone-500 font-mono tabular-nums">{s.estimated_duration_sec}s</span>
                </div>
                <div className="text-[10px] text-stone-700 line-clamp-2 leading-tight">
                  {s.visual_intent}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ================= RIGHT PANEL: SCENE PROPERTIES (3 Cols) ================= */}
        <div className="lg:col-span-3 bg-white border border-orange-200/80 rounded-2xl p-4 flex flex-col h-[740px] space-y-3.5 shadow-xs">
          <div className="border-b border-orange-100 pb-3">
            <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider flex items-center space-x-1.5">
              <Sliders className="w-4 h-4 text-orange-600" />
              <span>Thuộc tính Cảnh ({currentScene?.scene_id})</span>
            </h3>
          </div>

          <div className="space-y-3 flex-grow overflow-y-auto pr-1">
            {/* Visual Intent */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Ý đồ hình ảnh (Visual Intent):
              </label>
              <textarea
                rows={2}
                value={currentScene?.visual_intent || ''}
                onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'visual_intent', e.target.value)}
                className="w-full bg-stone-50 border border-orange-200 rounded-xl p-2.5 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
              />
            </div>

            {/* Narration */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Lời thuyết minh (Narration Text):
              </label>
              <textarea
                rows={4}
                value={currentScene?.narration || ''}
                onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'narration', e.target.value)}
                className="w-full bg-stone-50 border border-orange-200 rounded-xl p-2.5 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white leading-relaxed"
              />
            </div>

            {/* Duration */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Thời lượng cảnh (giây):
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="range"
                  min={2}
                  max={30}
                  value={currentScene?.estimated_duration_sec || 10}
                  onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'estimated_duration_sec', parseInt(e.target.value))}
                  className="w-full h-1.5 bg-stone-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                />
                <span className="font-mono text-xs text-stone-800 font-bold w-10 text-right tabular-nums">
                  {currentScene?.estimated_duration_sec}s
                </span>
              </div>
            </div>

            {/* Framing */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Góc quay (Camera Framing):
              </label>
              <select
                value={currentScene?.framing || 'Medium Shot'}
                onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'framing', e.target.value)}
                className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
              >
                <option value="Close-up">Cận cảnh (Close-up)</option>
                <option value="Medium Shot">Trung cảnh (Medium Shot)</option>
                <option value="Wide Shot">Toàn cảnh (Wide Shot)</option>
                <option value="Drone / Aerial">Góc nhìn Flycam (Drone)</option>
                <option value="Low Angle">Góc thấp quyền lực (Low Angle)</option>
              </select>
            </div>

            {/* Text Effect */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Hiệu ứng chữ (Text Effect):
              </label>
              <select
                value={currentScene?.text_effect || 'fade'}
                onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'text_effect', e.target.value)}
                className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
              >
                <option value="fade">Mờ dần (Fade in)</option>
                <option value="zoom_in">Phóng to (Cinematic Zoom)</option>
                <option value="typewriter">Đánh máy (Typewriter)</option>
                <option value="glitch">Glitch điện tử</option>
                <option value="slide_up">Trượt lên (Slide up)</option>
              </select>
            </div>

            {/* Voice Persona Preset */}
            <div>
              <label className="text-[11px] font-semibold text-stone-600 block mb-1">
                Giọng đọc TTS:
              </label>
              <select
                value={currentScene?.tts_profile || 'male_warm'}
                onChange={(e) => handleUpdateSceneField(activeSceneIndex, 'tts_profile', e.target.value)}
                className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white"
              >
                <option value="male_warm">Aoede (Trầm ấm - Tin tức)</option>
                <option value="female_bright">Kore (Trong trẻo - Kể chuyện)</option>
                <option value="male_hype">Puck (Hào hứng - TikTok)</option>
                <option value="authoritative">Charon (Uy quyền - Phóng sự)</option>
              </select>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
