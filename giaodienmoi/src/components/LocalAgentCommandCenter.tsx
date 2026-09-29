import React, { useState } from 'react';
import { 
  Server, Cpu, Play, Pause, Trash2, RotateCcw, 
  Check, Sparkles, RefreshCw, Zap,
  CheckCircle2, AlertTriangle, Layers, ThumbsUp, ThumbsDown
} from 'lucide-react';
import { AgentJob } from '../types';
import { ImageWithFallback } from './ImageWithFallback';

interface LocalAgentCommandCenterProps {
  jobs: AgentJob[];
  onUpdateJob: (id: string, status: AgentJob['status']) => void;
  onAddJob: (prompt: string, model: string) => void;
  onClearFailed: () => void;
  onRetryFailed: () => void;
}

export const LocalAgentCommandCenter: React.FC<LocalAgentCommandCenterProps> = ({
  jobs,
  onUpdateJob,
  onAddJob,
  onClearFailed,
  onRetryFailed
}) => {
  const [isPaused, setIsPaused] = useState(false);
  const [newPrompt, setNewPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('Flux.1-schnell / SDXL-Turbo');
  const [reviewMode, setReviewMode] = useState<'grid' | 'tinder'>('grid');
  const [tinderIndex, setTinderIndex] = useState(0);

  const agentMetadata = {
    ip: '192.168.1.105:7860',
    tunnel: 'https://7860-gpu-worker-ai.ngrok-free.app',
    latency: '18 ms',
    gpu: 'NVIDIA GeForce RTX 4090 (24GB VRAM)',
    vramUsed: '9.4 GB / 24.0 GB (39%)',
    quotaRemaining: '84%',
    rpmRemaining: '14 / 15 RPM',
    rpdRemaining: '1,280 / 1,500 RPD'
  };

  const pendingReviewJobs = jobs.filter(j => j.status === 'ready');
  const activeTinderJob = pendingReviewJobs[tinderIndex] || pendingReviewJobs[0];

  const handleTinderAction = (action: 'keep' | 'regenerate' | 'discard') => {
    if (!activeTinderJob) return;
    if (action === 'keep') onUpdateJob(activeTinderJob.id, 'kept');
    if (action === 'discard') onUpdateJob(activeTinderJob.id, 'discarded');
    if (action === 'regenerate') {
      onUpdateJob(activeTinderJob.id, 'queued');
    }
    if (tinderIndex < pendingReviewJobs.length - 1) {
      setTinderIndex(tinderIndex + 1);
    } else {
      setTinderIndex(0);
    }
  };

  const failedCount = jobs.filter(j => j.status === 'failed').length;

  return (
    <div className="space-y-6">
      {/* ================= TOP STATUS BAR ================= */}
      <div className="bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-orange-100 pb-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <h2 className="text-sm font-bold text-stone-900">
                  Local Agent Status: Connected (Máy Chủ Cục Bộ Sẵn Sàng)
                </h2>
                <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-bold">
                  {agentMetadata.latency}
                </span>
              </div>
              <p className="text-xs text-stone-500 mt-0.5 font-mono">
                Host: {agentMetadata.ip} · Ngrok Tunnel: {agentMetadata.tunnel}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* GPU Device */}
            <div className="bg-stone-50 border border-stone-200 px-3 py-1.5 rounded-xl text-xs flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-orange-600" />
              <div>
                <span className="text-stone-900 font-semibold">{agentMetadata.gpu}</span>
                <span className="text-[10px] text-stone-500 block font-mono">VRAM: {agentMetadata.vramUsed}</span>
              </div>
            </div>

            {/* Gemini API Quota */}
            <div className="bg-stone-50 border border-stone-200 px-3 py-1.5 rounded-xl text-xs flex items-center space-x-2">
              <Zap className="w-4 h-4 text-amber-500" />
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-stone-900 font-semibold">Gemini API Quota</span>
                  <span className="font-mono text-emerald-700 font-bold">{agentMetadata.quotaRemaining}</span>
                </div>
                <div className="w-24 bg-stone-200 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className="bg-emerald-500 h-full" style={{ width: agentMetadata.quotaRemaining }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Add Job Quick Dispatcher */}
        <div className="flex flex-col sm:flex-row gap-3 items-center">
          <div className="relative flex-grow w-full">
            <input
              type="text"
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              placeholder="Nhập prompt gửi thẳng tới Local Agent GPU (VD: Siêu xe Cyberpunk phóng trong mưa ban đêm, 8k cinematic)..."
              className="w-full bg-stone-50 border border-orange-200 rounded-xl px-4 py-2.5 text-xs text-stone-900 focus:outline-none focus:border-orange-500 focus:bg-white transition-colors"
            />
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto shrink-0">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-xs text-stone-900 focus:outline-none focus:border-orange-500"
            >
              <option value="Flux.1-schnell / SDXL-Turbo">Flux.1-schnell (Siêu tốc)</option>
              <option value="SDXL Cinematic V2">SDXL Cinematic V2</option>
              <option value="Realistic Vision 6.0">Realistic Vision 6.0</option>
              <option value="AnimateDiff Video">AnimateDiff Video</option>
            </select>

            <button
              onClick={() => {
                if (newPrompt.trim()) {
                  onAddJob(newPrompt, selectedModel);
                  setNewPrompt('');
                }
              }}
              disabled={!newPrompt.trim()}
              className="px-4 py-2.5 rounded-xl bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs shadow-xs disabled:opacity-40 transition-colors whitespace-nowrap"
            >
              Gửi Tạo Ảnh
            </button>
          </div>
        </div>
      </div>

      {/* ================= 2-COLUMN: BATCH QUEUE & REVIEW GRID ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: BATCH QUEUE (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-orange-100 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-orange-600" />
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                Batch Queue ({jobs.length} tác vụ)
              </h3>
            </div>

            {/* Queue Controls */}
            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => setIsPaused(!isPaused)}
                className={`p-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1 border ${
                  isPaused
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-stone-100 text-stone-700 border-stone-200 hover:bg-stone-200'
                }`}
                title={isPaused ? 'Tiếp tục xử lý' : 'Tạm dừng hàng đợi'}
              >
                {isPaused ? <Play className="w-3.5 h-3.5 fill-amber-700 text-amber-700" /> : <Pause className="w-3.5 h-3.5" />}
              </button>

              {failedCount > 0 && (
                <>
                  <button
                    onClick={onRetryFailed}
                    className="p-1.5 rounded-lg bg-orange-50 text-orange-700 border border-orange-200 hover:bg-orange-100 text-xs"
                    title="Chạy lại các tác vụ lỗi"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={onClearFailed}
                    className="p-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 text-xs"
                    title="Xóa tác vụ lỗi"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Queue Items List */}
          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
            {jobs.length === 0 ? (
              <div className="text-center py-12 text-stone-400 text-xs">
                Chưa có tác vụ nào trong hàng đợi
              </div>
            ) : (
              jobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-stone-50 border border-stone-200/80 rounded-xl p-3 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-stone-700 font-bold">
                      {job.scene_id || job.id}
                    </span>
                    <span className="text-[10px] text-stone-500 font-medium">
                      {job.model}
                    </span>
                  </div>

                  <p className="text-xs text-stone-800 line-clamp-2 leading-relaxed">
                    {job.prompt}
                  </p>

                  {/* Progress bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-semibold capitalize text-stone-600">
                        {job.status === 'processing' && <span className="text-orange-600 animate-pulse">Đang sinh ảnh...</span>}
                        {job.status === 'ready' && <span className="text-emerald-700 font-bold">Hoàn tất</span>}
                        {job.status === 'queued' && <span className="text-stone-500">Chờ lượt</span>}
                        {job.status === 'kept' && <span className="text-blue-700">Đã lưu kịch bản</span>}
                        {job.status === 'discarded' && <span className="text-stone-400">Đã loại</span>}
                        {job.status === 'failed' && <span className="text-rose-700 font-bold">Lỗi</span>}
                      </span>
                      <span className="font-mono text-stone-500 tabular-nums">{job.progress}%</span>
                    </div>
                    <div className="w-full bg-stone-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          job.status === 'ready' || job.status === 'kept'
                            ? 'bg-emerald-500'
                            : job.status === 'failed'
                            ? 'bg-rose-500'
                            : 'bg-orange-500'
                        }`}
                        style={{ width: `${job.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: REVIEW GRID (7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-orange-200/80 rounded-2xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-orange-100 pb-3">
            <div>
              <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wider">
                Duyệt Ảnh Hàng Loạt (Review Grid)
              </h3>
              <p className="text-[11px] text-stone-500">
                Chọn Giữ (Keep), Tạo Lại (Regenerate) hoặc Xóa (Discard)
              </p>
            </div>

            {/* Mode switch */}
            <div className="flex items-center space-x-1 bg-stone-100 p-1 rounded-xl border border-stone-200">
              <button
                onClick={() => setReviewMode('grid')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  reviewMode === 'grid'
                    ? 'bg-white text-orange-700 shadow-xs border border-orange-200/60'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                Grid 4 ảnh
              </button>
              <button
                onClick={() => setReviewMode('tinder')}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                  reviewMode === 'tinder'
                    ? 'bg-white text-orange-700 shadow-xs border border-orange-200/60'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                Vuốt Tinder
              </button>
            </div>
          </div>

          {/* Review Mode: Tinder View */}
          {reviewMode === 'tinder' && (
            <div className="flex flex-col items-center justify-center p-4">
              {activeTinderJob ? (
                <div className="w-full max-w-sm bg-stone-50 border border-orange-200 rounded-2xl overflow-hidden shadow-md space-y-3 p-4">
                  <div className="relative aspect-[9/16] max-h-[380px] bg-stone-900 rounded-xl overflow-hidden shadow-inner">
                    <ImageWithFallback
                      src={activeTinderJob.previewUrl}
                      alt={activeTinderJob.prompt}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2 bg-black/60 text-white font-mono text-[10px] px-2 py-0.5 rounded">
                      {activeTinderJob.scene_id}
                    </div>
                  </div>

                  <p className="text-xs text-stone-800 line-clamp-2 italic">
                    "{activeTinderJob.prompt}"
                  </p>

                  {/* Actions */}
                  <div className="grid grid-cols-3 gap-2 pt-2">
                    <button
                      onClick={() => handleTinderAction('discard')}
                      className="py-2.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-xs flex items-center justify-center space-x-1"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-stone-500" />
                      <span>Bỏ qua</span>
                    </button>
                    <button
                      onClick={() => handleTinderAction('regenerate')}
                      className="py-2.5 rounded-xl bg-orange-50 hover:bg-orange-100 text-orange-700 font-bold text-xs flex items-center justify-center space-x-1 border border-orange-200"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Tạo lại</span>
                    </button>
                    <button
                      onClick={() => handleTinderAction('keep')}
                      className="py-2.5 rounded-xl bg-orange-600 hover:bg-orange-700 text-white font-bold text-xs flex items-center justify-center space-x-1 shadow-xs"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Giữ lại</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-16 text-stone-400 text-xs">
                  Không còn ảnh nào chờ duyệt trong hàng đợi
                </div>
              )}
            </div>
          )}

          {/* Review Mode: Grid 4 Items */}
          {reviewMode === 'grid' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-stone-50 border border-stone-200 rounded-xl overflow-hidden shadow-2xs flex flex-col justify-between"
                >
                  <div className="relative h-44 bg-stone-900">
                    <ImageWithFallback
                      src={job.previewUrl}
                      alt={job.prompt}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2 bg-black/60 text-white font-mono text-[10px] px-2 py-0.5 rounded">
                      {job.scene_id || job.id}
                    </div>
                  </div>

                  <div className="p-3 space-y-2">
                    <p className="text-xs text-stone-800 line-clamp-2">
                      {job.prompt}
                    </p>

                    <div className="flex items-center space-x-1.5 pt-1">
                      <button
                        onClick={() => onUpdateJob(job.id, 'kept')}
                        className={`flex-1 py-1.5 rounded-lg text-xs font-bold transition-all ${
                          job.status === 'kept'
                            ? 'bg-emerald-600 text-white'
                            : 'bg-orange-600 hover:bg-orange-700 text-white'
                        }`}
                      >
                        {job.status === 'kept' ? 'Đã lưu' : 'Giữ (Keep)'}
                      </button>
                      <button
                        onClick={() => onUpdateJob(job.id, 'queued')}
                        className="p-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-200"
                        title="Tạo lại"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onUpdateJob(job.id, 'discarded')}
                        className="p-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 border border-stone-200"
                        title="Xóa"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
