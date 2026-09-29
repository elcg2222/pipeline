import React, { useState, useEffect, useCallback } from 'react';
import { Header, TabType } from './components/Header';
import { SmartResearchHub } from './components/SmartResearchHub';
import { ScriptStoryboardWorkspace } from './components/ScriptStoryboardWorkspace';
import { BatchPipelineStudio } from './components/BatchPipelineStudio';
import { LocalAgentCommandCenter } from './components/LocalAgentCommandCenter';
import { MiniVideoEditor } from './components/MiniVideoEditor';
import { PipelineMonitor } from './components/PipelineMonitor';
import { KaggleHandoff } from './components/KaggleHandoff';
import { Sparkles, X, Wand2, Rocket } from 'lucide-react';
import { 
  VideoItem, RunItem, ProjectSummary, ProjectDetail, 
  SceneItem, ResearchAsset, AgentJob, BatchVideoVariant 
} from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('research');
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [summary, setSummary] = useState<{
    states: Record<string, number>;
    platforms: Record<string, number>;
    job: {
      command: string | null;
      started: number | null;
      output: string;
    };
  }>({
    states: {},
    platforms: {},
    job: { command: null, started: null, output: '' }
  });

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [currentProjectId, setCurrentProjectId] = useState<string>('');
  const [currentProject, setCurrentProject] = useState<ProjectDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // 1-Click Batch Wizard Modal State
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [wizardTopic, setWizardTopic] = useState('Trí tuệ nhân tạo và Robot 2026');
  const [wizardRatio, setWizardRatio] = useState<'9:16' | '16:9'>('9:16');
  const [wizardStyle, setWizardStyle] = useState('Viral Hook + Cinematic B-Roll');

  // Toast Notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Local Agent Jobs State
  const [agentJobs, setAgentJobs] = useState<AgentJob[]>([
    {
      id: 'job_001',
      scene_id: 'scene_001',
      prompt: 'Cinematic hyperrealistic humanoid robot inspecting high-tech semiconductor motherboard in cleanroom, dramatic warm amber lighting, 8k resolution',
      model: 'Flux.1-schnell / SDXL-Turbo',
      status: 'ready',
      progress: 100,
      previewUrl: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now() - 120000
    },
    {
      id: 'job_002',
      scene_id: 'scene_002',
      prompt: 'Futuristic virtual production LED wall with Unreal Engine 5.5 realistic sci-fi cityscape, camera rig, glowing anamorphic lens flare',
      model: 'SDXL Cinematic V2',
      status: 'ready',
      progress: 100,
      previewUrl: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now() - 60000
    },
    {
      id: 'job_003',
      scene_id: 'scene_003',
      prompt: 'Cyberpunk neon street at night with glowing holographic advertisements and reflections on wet asphalt, volumetric warm fog, cinematic wide angle',
      model: 'Flux.1-schnell / SDXL-Turbo',
      status: 'processing',
      progress: 68,
      previewUrl: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now() - 20000
    },
    {
      id: 'job_004',
      scene_id: 'scene_004',
      prompt: 'Close-up of advanced 2nm silicon wafer glistening under laboratory laser light, precision robotics arm in background',
      model: 'Flux.1-schnell / SDXL-Turbo',
      status: 'queued',
      progress: 12,
      previewUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now() - 5000
    }
  ]);

  // Agent Progress Ticker
  useEffect(() => {
    const interval = setInterval(() => {
      setAgentJobs((prevJobs) =>
        prevJobs.map((job) => {
          if (job.status === 'processing') {
            const nextProgress = job.progress + 8;
            if (nextProgress >= 100) {
              return { ...job, progress: 100, status: 'ready' };
            }
            return { ...job, progress: nextProgress };
          }
          if (job.status === 'queued') {
            return { ...job, status: 'processing', progress: 15 };
          }
          return job;
        })
      );
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Fetch pipeline data
  const fetchPipelineData = useCallback(async () => {
    try {
      const [sumRes, vidRes, runRes] = await Promise.all([
        fetch('/api/summary'),
        fetch('/api/videos'),
        fetch('/api/runs')
      ]);

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        setSummary(sumData);
      }
      if (vidRes.ok) {
        const vidData = await vidRes.json();
        setVideos(vidData.rows || []);
      }
      if (runRes.ok) {
        const runData = await runRes.json();
        setRuns(runData.rows || []);
      }
    } catch (e) {
      console.warn('Error fetching pipeline data:', e);
    }
  }, []);

  // Fetch projects list
  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch('/api/projects');
      if (res.ok) {
        const data = await res.json();
        const projs: ProjectSummary[] = data.projects || [];
        setProjects(projs);
        if (projs.length > 0 && !currentProjectId) {
          setCurrentProjectId(projs[0].id);
        }
      }
    } catch (e) {
      console.warn('Error fetching projects:', e);
    }
  }, [currentProjectId]);

  // Fetch single project detail
  const fetchProjectDetail = useCallback(async (id: string) => {
    if (!id) return;
    try {
      const res = await fetch(`/api/projects/${id}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentProject(data);
      }
    } catch (e) {
      console.warn('Error fetching project detail:', e);
    }
  }, []);

  useEffect(() => {
    fetchPipelineData();
    fetchProjects();
  }, [fetchPipelineData, fetchProjects]);

  useEffect(() => {
    if (currentProjectId) {
      fetchProjectDetail(currentProjectId);
    }
  }, [currentProjectId, fetchProjectDetail]);

  // Push asset from Smart Research Hub to Script
  const handlePushAssetToScript = (asset: ResearchAsset) => {
    if (!currentProject) return;

    const newIdx = currentProject.scenes.length + 1;
    const newScene: SceneItem = {
      scene_id: `scene_${String(newIdx).padStart(3, '0')}`,
      chapter_id: `Phân đoạn: ${asset.source.toUpperCase()}`,
      narration: asset.summary || asset.title,
      estimated_duration_sec: 10,
      visual_intent: asset.title,
      status: 'ready',
      format: currentProject.brief.aspect_ratio || '9:16',
      tts_profile: 'male_warm',
      media: asset.previewUrl
    };

    const updatedScenes = [...currentProject.scenes, newScene];
    handleUpdateScenes(updatedScenes);
    showToast(`Đã thêm "${asset.title.slice(0, 30)}..." vào Kịch bản (Scene ${newIdx})`);
  };

  // Push prompt to Agent
  const handleSendPromptToAgent = (prompt: string, asset?: ResearchAsset) => {
    const newJob: AgentJob = {
      id: `job_${Date.now().toString().slice(-4)}`,
      scene_id: `scene_${String(agentJobs.length + 1).padStart(3, '0')}`,
      prompt,
      model: 'Flux.1-schnell / SDXL-Turbo',
      status: 'processing',
      progress: 20,
      previewUrl: asset?.previewUrl || 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now()
    };
    setAgentJobs(prev => [newJob, ...prev]);
    showToast(`Đã gửi prompt tới Local Agent GPU!`);
  };

  // Send batch from Storyboard to Agent
  const handleSendBatchToAgent = (scenesToBatch: SceneItem[]) => {
    const newJobs: AgentJob[] = scenesToBatch.map((s, idx) => ({
      id: `batch_${Date.now()}_${idx}`,
      scene_id: s.scene_id,
      prompt: `Cinematic visualization of: ${s.visual_intent || s.narration}. High detail, 8k photorealistic.`,
      model: 'Flux.1-schnell / SDXL-Turbo',
      status: idx === 0 ? 'processing' : 'queued',
      progress: idx === 0 ? 30 : 0,
      previewUrl: s.media || 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80',
      createdAt: Date.now()
    }));

    setAgentJobs(prev => [...newJobs, ...prev]);
    showToast(`Đã đẩy ${scenesToBatch.length} cảnh vào hàng đợi sinh ảnh Local Agent!`);
  };

  const handleUpdateJob = (id: string, status: AgentJob['status']) => {
    setAgentJobs(prev =>
      prev.map(j => {
        if (j.id === id) {
          if (status === 'kept' && currentProject && j.scene_id) {
            const updated = currentProject.scenes.map(s =>
              s.scene_id === j.scene_id ? { ...s, media: j.previewUrl } : s
            );
            handleUpdateScenes(updated);
            showToast(`Đã lưu ảnh vào Cảnh ${j.scene_id}!`);
          }
          return { ...j, status };
        }
        return j;
      })
    );
  };

  const handleClearFailed = () => {
    setAgentJobs(prev => prev.filter(j => j.status !== 'failed'));
    showToast('Đã dọn dẹp các tác vụ lỗi');
  };

  const handleRetryFailed = () => {
    setAgentJobs(prev =>
      prev.map(j => j.status === 'failed' ? { ...j, status: 'queued', progress: 0 } : j)
    );
    showToast('Đã đưa các tác vụ lỗi trở lại hàng đợi');
  };

  const handleUpdateScenes = async (newScenes: SceneItem[]) => {
    if (!currentProject) return;
    try {
      await fetch(`/api/projects/${currentProject.id}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenes: newScenes })
      });
      setCurrentProject(prev => prev ? { ...prev, scenes: newScenes } : null);
    } catch (e) {
      console.error('Failed to update scenes:', e);
    }
  };

  const handleRunCommand = async (command: string, urls?: string[]) => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, urls })
      });
      const data = await res.json();
      if (!res.ok && data.error) {
        alert(data.error);
      } else {
        await fetchPipelineData();
      }
    } catch (e) {
      console.error('Run command failed:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // 1-Click Wizard Execution
  const handleExecuteBatchWizard = () => {
    setIsWizardOpen(false);
    setActiveTab('batch');
    showToast(`Đã kích hoạt Ma Trận Tạo 10 Video cho chủ đề "${wizardTopic}"!`);
  };

  const totalPassed = summary.states['qc_passed'] || 0;

  const activeScenes = currentProject?.scenes && currentProject.scenes.length > 0 
    ? currentProject.scenes 
    : [
        {
          scene_id: 'scene_001',
          chapter_id: 'Phân đoạn 1',
          narration: 'Không ồn ào phô trương, các đại biểu bước vào phòng họp công nghệ cao...',
          estimated_duration_sec: 10,
          visual_intent: 'Cảnh 1: Khung cảnh công nghệ cao tương lai',
          status: 'ready',
          format: '9:16',
          media: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80'
        },
        {
          scene_id: 'scene_002',
          chapter_id: 'Phân đoạn 2',
          narration: 'Một cái gật đầu kín đáo phát đi thông điệp: Cuộc cách mạng AI đã chính thức bắt đầu.',
          estimated_duration_sec: 12,
          visual_intent: 'Cảnh 2: Tín hiệu đột phá và giao diện mạng thần kinh',
          status: 'ready',
          format: '9:16',
          media: 'https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?auto=format&fit=crop&w=600&q=80'
        }
      ];

  return (
    <div className="min-h-screen bg-[#fbf8f4] text-stone-900 flex flex-col font-sans selection:bg-orange-500 selection:text-white">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 right-6 z-50 bg-stone-900 text-white font-medium text-xs px-4 py-2.5 rounded-xl shadow-xl border border-stone-700 animate-fade-in flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Global Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        totalVideos={videos.length}
        totalPassed={totalPassed}
        totalProjects={projects.length}
        isProcessing={!!summary.job.command}
        agentConnected={true}
        onOpenBatchWizard={() => setIsWizardOpen(true)}
      />

      {/* 1-Click Batch Video Wizard Modal */}
      {isWizardOpen && (
        <div className="fixed inset-0 z-50 bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-orange-200 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-scale-up">
            <div className="flex items-center justify-between border-b border-orange-100 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-orange-100 text-orange-600 flex items-center justify-center font-bold">
                  <Rocket className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    Trợ Lý Tạo 10 Video Hàng Loạt (Batch Wizard)
                  </h3>
                  <p className="text-[11px] text-stone-500">
                    Tự động tạo ma trận Hook x Visual Style x TTS giọng đọc
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsWizardOpen(false)}
                className="text-stone-400 hover:text-stone-700 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Topic Input */}
              <div>
                <label className="font-semibold text-stone-700 block mb-1">
                  1. Nhập chủ đề hoặc từ khóa chính:
                </label>
                <input
                  type="text"
                  value={wizardTopic}
                  onChange={(e) => setWizardTopic(e.target.value)}
                  placeholder="VD: Trí tuệ nhân tạo, Xe điện thông minh, Bài học tài chính..."
                  className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3.5 py-2.5 text-stone-900 focus:outline-none focus:border-orange-500 font-medium"
                />
              </div>

              {/* Aspect Ratio */}
              <div>
                <label className="font-semibold text-stone-700 block mb-1">
                  2. Định dạng video mục tiêu:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setWizardRatio('9:16')}
                    className={`py-2 px-3 rounded-xl border text-center font-semibold transition-all ${
                      wizardRatio === '9:16'
                        ? 'bg-orange-50 border-orange-500 text-orange-900 ring-1 ring-orange-500/20'
                        : 'bg-stone-50 border-stone-200 text-stone-600 hover:border-orange-300'
                    }`}
                  >
                    9:16 (TikTok / Reels / Shorts)
                  </button>
                  <button
                    type="button"
                    onClick={() => setWizardRatio('16:9')}
                    className={`py-2 px-3 rounded-xl border text-center font-semibold transition-all ${
                      wizardRatio === '16:9'
                        ? 'bg-orange-50 border-orange-500 text-orange-900 ring-1 ring-orange-500/20'
                        : 'bg-stone-50 border-stone-200 text-stone-600 hover:border-orange-300'
                    }`}
                  >
                    16:9 (YouTube Video Dài)
                  </button>
                </div>
              </div>

              {/* Style Strategy */}
              <div>
                <label className="font-semibold text-stone-700 block mb-1">
                  3. Chiến lược phân bổ phong cách:
                </label>
                <select
                  value={wizardStyle}
                  onChange={(e) => setWizardStyle(e.target.value)}
                  className="w-full bg-stone-50 border border-orange-200 rounded-xl px-3 py-2 text-stone-900 focus:outline-none focus:border-orange-500"
                >
                  <option value="Viral Hook + Cinematic B-Roll">Ma trận Viral: 5 Hook giật gân + 5 Hook tò mò</option>
                  <option value="Educational Authority">Phong cách Chuyên gia: So sánh số liệu & Bằng chứng thực tế</option>
                  <option value="Storytelling Drama">Kịch bản Kể chuyện kịch tính: Twist mở đầu & Cú lật kết thúc</option>
                </select>
              </div>

              <div className="bg-orange-50/70 p-3 rounded-xl border border-orange-200 text-[11px] text-stone-600 space-y-1">
                <div className="font-semibold text-orange-900">Quy trình tự động hóa sẽ thực hiện:</div>
                <div className="flex items-center space-x-1.5">
                  <span>✓</span>
                  <span>Sinh 10 biến thể kịch bản với các câu mở đầu khác biệt (A/B testing)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span>✓</span>
                  <span>Tự động gán giọng đọc phù hợp (Nam Bắc trầm, Nữ Nam trong trẻo)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span>✓</span>
                  <span>Áp dụng mẫu phụ đề động Alex Hormozi tự căn lề an toàn safe-zone</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-orange-100">
              <button
                type="button"
                onClick={() => setIsWizardOpen(false)}
                className="px-4 py-2 rounded-xl text-stone-600 hover:bg-stone-100 text-xs font-semibold"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleExecuteBatchWizard}
                className="flex items-center space-x-1.5 px-5 py-2.5 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-xl text-xs font-bold shadow-xs active:scale-95 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                <span>🚀 Khởi Chạy 10 Video Ngay</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace Area */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 grow">
        {/* 1 · Smart Research Hub */}
        {activeTab === 'research' && (
          <SmartResearchHub
            onPushToScript={handlePushAssetToScript}
            onSendToAgent={handleSendPromptToAgent}
          />
        )}

        {/* 2 · Script & Storyboard Workspace */}
        {activeTab === 'storyboard' && (
          <ScriptStoryboardWorkspace
            scenes={activeScenes}
            onUpdateScenes={handleUpdateScenes}
            onSendBatchToAgent={handleSendBatchToAgent}
            aspectRatio={currentProject?.brief.aspect_ratio || '9:16'}
          />
        )}

        {/* 3 · Batch Video Pipeline Studio (Ma trận tạo video hàng loạt) */}
        {activeTab === 'batch' && (
          <BatchPipelineStudio
            baseScenes={activeScenes}
            projectName={currentProject?.brief.title || 'Social_Trend_Batch'}
            onSendBatchToColab={(variants) => {
              showToast(`Đã đóng gói ${variants.length} video sẵn sàng xuất sang Colab / Kaggle!`);
            }}
          />
        )}

        {/* 4 · Local Agent Command Center */}
        {activeTab === 'command' && (
          <LocalAgentCommandCenter
            jobs={agentJobs}
            onUpdateJob={handleUpdateJob}
            onAddJob={(prompt, model) => {
              const newJob: AgentJob = {
                id: `job_${Date.now().toString().slice(-4)}`,
                prompt,
                model,
                status: 'queued',
                progress: 0,
                previewUrl: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80',
                createdAt: Date.now()
              };
              setAgentJobs(prev => [newJob, ...prev]);
              showToast('Đã thêm tác vụ mới vào hàng đợi');
            }}
            onClearFailed={handleClearFailed}
            onRetryFailed={handleRetryFailed}
          />
        )}

        {/* 5 · Mini Video Editor (CapCut Style) */}
        {activeTab === 'editor' && (
          <MiniVideoEditor
            scenes={activeScenes}
            availableAssets={[]}
            projectName={currentProject?.brief.title || 'Social_Trend_Video'}
          />
        )}

        {/* Database SQLite */}
        {activeTab === 'monitor' && (
          <PipelineMonitor
            videos={videos}
            runs={runs}
            summary={summary}
            onRunCommand={handleRunCommand}
            isLoading={isLoading}
            refreshData={fetchPipelineData}
          />
        )}

        {/* Kaggle Flow3 Export Handoff */}
        {activeTab === 'handoff' && (
          <KaggleHandoff currentProject={currentProject} />
        )}
      </main>

      {/* Global Footer (Quiet, clean typography, anti-slop) */}
      <footer className="border-t border-orange-200/80 py-4 bg-white text-xs text-stone-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-stone-700 font-medium">Social Video Studio v3.0 · Giao diện Tông Cam Sáng Hiện Đại</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] text-stone-500">
            <span>Local Agent: 192.168.1.105:7860</span>
            <span aria-hidden="true">·</span>
            <span>Batch Matrix Engine Active</span>
            <span aria-hidden="true">·</span>
            <span>Kaggle Flow3 Ready</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
