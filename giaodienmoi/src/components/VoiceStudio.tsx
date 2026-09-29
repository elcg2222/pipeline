import React, { useState, useRef, useEffect } from 'react';
import { 
  Mic, Play, Pause, RotateCcw, Sliders, Volume2, 
  Check, Save, Sparkles, Music, Waves, History
} from 'lucide-react';
import { SceneItem } from '../types';

interface VoiceStudioProps {
  activeScene?: SceneItem;
  onAttachToScene?: (settings: any) => void;
}

export const VoiceStudio: React.FC<VoiceStudioProps> = ({
  activeScene,
  onAttachToScene
}) => {
  // TTS Settings
  const [language, setLanguage] = useState('vi-VN');
  const [accent, setAccent] = useState('north'); // north, central, south
  const [persona, setPersona] = useState('Aoede'); // Aoede, Kore, Puck, Charon, Fenrir
  const [textPrompt, setTextPrompt] = useState(
    activeScene?.narration || 'Chào mừng các bạn đến với bản tin tổng hợp xu hướng mạng xã hội hôm nay.'
  );

  // Audio DSP knobs
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [volume, setVolume] = useState(100);
  const [reverb, setReverb] = useState(0);

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [history, setHistory] = useState<Array<{ id: string; time: string; text: string; persona: string }>>([
    {
      id: 'samp_1',
      time: '10:15',
      text: 'Chào mừng các bạn đến với bản tin tổng hợp xu hướng...',
      persona: 'Aoede (Bắc)'
    }
  ]);
  const [attached, setAttached] = useState(false);

  // Web Audio Context for preview sound synthesis
  const audioContextRef = useRef<AudioContext | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Update prompt when scene narration changes
  useEffect(() => {
    if (activeScene?.narration) {
      setTextPrompt(activeScene.narration);
    }
  }, [activeScene]);

  // Waveform visualization animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const mid = height / 2;

      ctx.beginPath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = isPlaying ? '#38bdf8' : '#334155';

      for (let x = 0; x < width; x++) {
        const freq = isPlaying ? 0.05 * speed : 0.02;
        const amp = isPlaying ? (height / 3) * (volume / 100) : 4;
        const y = mid + Math.sin(x * freq + phase) * amp;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      if (isPlaying) {
        phase += 0.15 * speed;
      }
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, speed, volume]);

  const handleGenerateSample = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      playSynthAudio();
      setHistory(prev => [
        {
          id: `samp_${Date.now()}`,
          time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
          text: textPrompt.slice(0, 50) + '...',
          persona: `${persona} (${accent === 'north' ? 'Bắc' : accent === 'central' ? 'Trung' : 'Nam'})`
        },
        ...prev.slice(0, 7)
      ]);
    }, 600);
  };

  const playSynthAudio = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioCtx();
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      setIsPlaying(true);

      // Play synthesized harmonic tone corresponding to speech pitch and duration
      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();

      const baseFreq = persona === 'Aoede' ? 140 : persona === 'Kore' ? 220 : persona === 'Puck' ? 190 : 120;
      const noteFreq = baseFreq * Math.pow(2, pitch / 12);

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(noteFreq, ctx.currentTime);

      // Pitch vibrato simulation
      osc.frequency.exponentialRampToValueAtTime(noteFreq * 1.05, ctx.currentTime + 0.3);
      osc.frequency.exponentialRampToValueAtTime(noteFreq * 0.98, ctx.currentTime + 0.8);

      const dur = Math.min(3.5, (textPrompt.length * 0.05) / speed);
      gainNode.gain.setValueAtTime((volume / 100) * 0.25, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);

      osc.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + dur);

      setTimeout(() => {
        setIsPlaying(false);
      }, dur * 1000);
    } catch {
      setIsPlaying(false);
    }
  };

  const handleAttach = () => {
    if (onAttachToScene) {
      onAttachToScene({
        language,
        accent,
        persona,
        speed,
        pitch,
        volume,
        reverb
      });
      setAttached(true);
      setTimeout(() => setAttached(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Description */}
      <div className="bg-[#171a23] border border-[#262b38] rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Mic className="w-5 h-5 text-blue-400" />
            <span>Voice Studio & TTS AI (Gemini 3.8 Flash TTS Engine)</span>
          </h2>
          <p className="text-xs text-[#8b90a0] mt-1">
            Hỗ trợ 3 miền Bắc / Trung / Nam · 5 phong cách nhân vật · Xử lý cao độ, tốc độ & vang âm local.
          </p>
        </div>

        {activeScene && (
          <div className="flex items-center space-x-2 bg-[#10131b] border border-[#262b38] px-3 py-1.5 rounded-xl text-xs">
            <span className="text-[#8b90a0]">Đang chọn cảnh:</span>
            <span className="font-semibold text-blue-400">{activeScene.scene_id}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: TTS Persona & Text Editor (7 cols) */}
        <div className="lg:col-span-7 bg-[#171a23] border border-[#262b38] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span>Thiết lập giọng đọc</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Language */}
            <div>
              <label className="text-xs text-[#8b90a0] block mb-1">Ngôn ngữ:</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full bg-[#10131b] border border-[#262b38] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="vi-VN">Tiếng Việt</option>
                <option value="en-US">English (US)</option>
                <option value="en-GB">English (UK)</option>
                <option value="zh-CN">中文 (Chinese)</option>
                <option value="ja-JP">日本語 (Japanese)</option>
              </select>
            </div>

            {/* Accent (Vietnamese) */}
            <div>
              <label className="text-xs text-[#8b90a0] block mb-1">Vùng giọng (Accent):</label>
              <select
                value={accent}
                onChange={(e) => setAccent(e.target.value)}
                disabled={language !== 'vi-VN'}
                className="w-full bg-[#10131b] border border-[#262b38] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
              >
                <option value="north">Miền Bắc (Hà Nội chuẩn)</option>
                <option value="central">Miền Trung (Huế/Đà Nẵng)</option>
                <option value="south">Miền Nam (Sài Gòn)</option>
              </select>
            </div>

            {/* Persona */}
            <div>
              <label className="text-xs text-[#8b90a0] block mb-1">Nhân vật (Persona):</label>
              <select
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
                className="w-full bg-[#10131b] border border-[#262b38] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option value="Aoede">Aoede (Trầm ấm, tin tức)</option>
                <option value="Kore">Kore (Trong trẻo, tươi sáng)</option>
                <option value="Puck">Puck (Hào hứng, sôi động)</option>
                <option value="Charon">Charon (Uy quyền, phóng sự)</option>
                <option value="Fenrir">Fenrir (Mạnh mẽ, kịch tính)</option>
              </select>
            </div>
          </div>

          {/* Script Textarea */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs text-[#8b90a0]">Nội dung cần chuyển thành giọng nói:</label>
              <span className={`text-[11px] font-mono ${textPrompt.length > 1500 ? 'text-rose-400' : 'text-[#8b90a0]'}`}>
                {textPrompt.length} / 1500 ký tự
              </span>
            </div>
            <textarea
              rows={6}
              value={textPrompt}
              maxLength={1500}
              onChange={(e) => setTextPrompt(e.target.value)}
              placeholder="Nhập nội dung thuyết minh cần đọc..."
              className="w-full bg-[#10131b] border border-[#262b38] rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <button
              onClick={handleGenerateSample}
              disabled={isGenerating || !textPrompt.trim()}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-md transition-all disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin" />
                  <span>Đang tổng hợp giọng nói...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Tạo đoạn mẫu TTS & Nghe thử</span>
                </>
              )}
            </button>

            {onAttachToScene && (
              <button
                onClick={handleAttach}
                className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-colors"
              >
                {attached ? (
                  <>
                    <Check className="w-4 h-4 text-white" />
                    <span>Đã gắn vào cảnh</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Gắn vào cảnh {activeScene?.scene_id || ''}</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Right Column: Audio DSP Tuning & Visualizer (5 cols) */}
        <div className="lg:col-span-5 bg-[#171a23] border border-[#262b38] rounded-2xl p-5 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-blue-400" />
            <span>Bộ chỉnh âm sắc Local (DSP)</span>
          </h3>

          {/* Waveform Canvas */}
          <div className="bg-[#10131b] border border-[#262b38] rounded-xl p-3 flex flex-col items-center justify-center">
            <canvas
              ref={canvasRef}
              width={380}
              height={70}
              className="w-full h-16 rounded"
            />
            <div className="flex items-center justify-between w-full text-[11px] text-[#8b90a0] mt-1 px-1">
              <span>{isPlaying ? '● Đang phát' : '○ Sẵn sàng'}</span>
              <span>48,000 Hz · Stereo 16-bit</span>
            </div>
          </div>

          {/* Knobs & Sliders */}
          <div className="space-y-3">
            {/* Speed */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-[#8b90a0]">Tốc độ đọc (Speed):</span>
                <span className="text-white font-mono font-semibold">{speed.toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min={0.5}
                max={2.0}
                step={0.1}
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            {/* Pitch */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-[#8b90a0]">Cao độ (Pitch):</span>
                <span className="text-white font-mono font-semibold">{pitch > 0 ? `+${pitch}` : pitch} semitones</span>
              </div>
              <input
                type="range"
                min={-5}
                max={5}
                step={1}
                value={pitch}
                onChange={(e) => setPitch(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            {/* Volume */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-[#8b90a0]">Âm lượng (Volume):</span>
                <span className="text-white font-mono font-semibold">{volume}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={150}
                step={5}
                value={volume}
                onChange={(e) => setVolume(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            {/* Reverb / Echo */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-[#8b90a0]">Độ vang nhẹ (Reverb / Echo):</span>
                <span className="text-white font-mono font-semibold">{reverb}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={50}
                step={5}
                value={reverb}
                onChange={(e) => setReverb(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-[#262b38] rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          </div>

          {/* Reset button */}
          <div className="pt-2">
            <button
              onClick={() => {
                setSpeed(1.0);
                setPitch(0);
                setVolume(100);
                setReverb(0);
              }}
              className="text-xs text-[#8b90a0] hover:text-white flex items-center space-x-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Khôi phục thông số mặc định</span>
            </button>
          </div>

          {/* Session History */}
          <div className="pt-3 border-t border-[#262b38]">
            <h4 className="text-xs font-semibold text-white mb-2 flex items-center space-x-1.5">
              <History className="w-3.5 h-3.5 text-blue-400" />
              <span>Lịch sử mẫu vừa tạo ({history.length})</span>
            </h4>
            <div className="space-y-1.5 max-h-32 overflow-y-auto">
              {history.map((item) => (
                <div 
                  key={item.id}
                  onClick={playSynthAudio}
                  className="p-2 rounded-lg bg-[#10131b] border border-[#262b38] text-[11px] flex items-center justify-between cursor-pointer hover:border-blue-500"
                >
                  <span className="text-white truncate max-w-[200px]">{item.text}</span>
                  <span className="text-[#8b90a0] font-mono">{item.persona}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
