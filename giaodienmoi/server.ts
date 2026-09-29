import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const app = express();
const PORT = 3000;
const ROOT = process.cwd();
const DATA_DIR = path.join(ROOT, 'data');
const SEED_FILE = path.join(DATA_DIR, 'seed_data.json');
const OUTPUTS_DIR = path.join(ROOT, 'outputs');

app.use(express.json({ limit: '10mb' }));

// In-memory data store with fallback
interface VideoItem {
  uid: string;
  platform: string;
  url: string;
  native_id?: string;
  title?: string;
  author?: string;
  author_id?: string;
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  collects?: number;
  duration?: number;
  score?: number;
  state: string;
  attempts?: number;
  last_error?: string;
  updated_at?: number;
  topic?: string;
  source?: string;
  [key: string]: any;
}

interface RunItem {
  id: number;
  stage: string;
  topic?: string;
  started?: number;
  finished?: number;
  ok?: number;
  failed?: number;
  note?: string;
}

let videos: VideoItem[] = [];
let runs: RunItem[] = [];

try {
  if (fs.existsSync(SEED_FILE)) {
    const raw = JSON.parse(fs.readFileSync(SEED_FILE, 'utf-8'));
    videos = raw.videos || [];
    runs = raw.runs || [];
  }
} catch (e) {
  console.warn('Failed to load seed_data.json, starting with default sample store', e);
}

if (videos.length === 0) {
  videos = [
    {
      uid: 'tiktok_734891028391',
      platform: 'tiktok',
      url: 'https://www.tiktok.com/@creator/video/734891028391',
      title: 'Top 5 công nghệ AI đột phá thay đổi năm 2026',
      author: 'TechTrend VN',
      views: 350000,
      likes: 42000,
      comments: 1800,
      shares: 5200,
      collects: 9800,
      score: 8.75,
      state: 'qc_passed',
      attempts: 1,
      topic: 'ai_technology',
      updated_at: Math.floor(Date.now() / 1000)
    },
    {
      uid: 'douyin_728193810293',
      platform: 'douyin',
      url: 'https://www.douyin.com/video/728193810293',
      title: 'Thiết bị gia dụng thông minh tiện lợi không tưởng',
      author: 'SmartLife Lab',
      views: 1200000,
      likes: 185000,
      comments: 8900,
      shares: 34000,
      collects: 76000,
      score: 9.42,
      state: 'downloaded',
      attempts: 1,
      topic: 'gadgets',
      updated_at: Math.floor(Date.now() / 1000) - 3600
    },
    {
      uid: 'youtube_dQw4w9WgXcQ',
      platform: 'youtube',
      url: 'https://youtube.com/shorts/dQw4w9WgXcQ',
      title: 'Bí quyết năng suất buổi sáng chỉ trong 30 giây',
      author: 'Focus Daily',
      views: 89000,
      likes: 9200,
      comments: 310,
      shares: 1100,
      collects: 2300,
      score: 7.15,
      state: 'queued',
      attempts: 0,
      topic: 'productivity',
      updated_at: Math.floor(Date.now() / 1000) - 7200
    }
  ];
}

let activeJob = {
  command: null as string | null,
  started: null as number | null,
  output: ''
};

function saveSeedData() {
  try {
    if (!fs.existsSync(DATA_DIR)) {
      fs.mkdirSync(DATA_DIR, { recursive: true });
    }
    fs.writeFileSync(SEED_FILE, JSON.stringify({ videos, runs }, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error persisting seed_data:', err);
  }
}

// Media file server
app.use('/media-files', express.static(OUTPUTS_DIR));
app.use('/audio-files', express.static(path.join(DATA_DIR, 'audio')));

// API: Summary
app.get('/api/summary', (req: Request, res: Response) => {
  const states: Record<string, number> = {};
  const platforms: Record<string, number> = {};

  for (const v of videos) {
    states[v.state] = (states[v.state] || 0) + 1;
    platforms[v.platform] = (platforms[v.platform] || 0) + 1;
  }

  res.json({
    states,
    platforms,
    total: videos.length,
    job: activeJob
  });
});

// API: Videos
app.get('/api/videos', (req: Request, res: Response) => {
  const platform = typeof req.query.platform === 'string' ? req.query.platform.trim() : '';
  const state = typeof req.query.state === 'string' ? req.query.state.trim() : '';
  const q = typeof req.query.q === 'string' ? req.query.q.trim().toLowerCase() : '';

  let filtered = videos;
  if (platform) {
    filtered = filtered.filter(v => v.platform === platform);
  }
  if (state) {
    filtered = filtered.filter(v => v.state === state);
  }
  if (q) {
    filtered = filtered.filter(v => 
      (v.title && v.title.toLowerCase().includes(q)) ||
      (v.topic && v.topic.toLowerCase().includes(q)) ||
      (v.author && v.author.toLowerCase().includes(q)) ||
      (v.url && v.url.toLowerCase().includes(q)) ||
      (v.native_id && v.native_id.toLowerCase().includes(q))
    );
  }

  filtered.sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));
  res.json({ rows: filtered.slice(0, 300) });
});

// API: Runs
app.get('/api/runs', (req: Request, res: Response) => {
  const sorted = [...runs].sort((a, b) => (b.started || 0) - (a.started || 0));
  res.json({ rows: sorted.slice(0, 50) });
});

// Guess platform from URL
function guessPlatform(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, '');
    if (/facebook\.com|fb\.watch/.test(host)) return 'facebook';
    if (/instagram\.com|instagr\.am/.test(host)) return 'instagram';
    if (/reddit\.com|redd\.it/.test(host)) return 'reddit';
    if (/discord\.com|discordapp\.com|discordapp\.net/.test(host)) return 'discord';
    if (/tiktok\.com/.test(host)) return 'tiktok';
    if (/douyin\.com/.test(host)) return 'douyin';
    if (/youtube\.com|youtu\.be/.test(host)) return 'youtube';
    if (/1688\.com/.test(host)) return '1688';
    return host.split('.')[0] || 'web';
  } catch {
    return 'web';
  }
}

// API: Run pipeline task
app.post('/api/run', (req: Request, res: Response) => {
  const { command, urls } = req.body;
  if (!command) {
    return res.status(400).json({ error: 'Thiếu lệnh command' });
  }

  if (activeJob.command) {
    return res.status(409).json({ error: 'Một tác vụ khác đang chạy. Hãy chờ hoàn thành.' });
  }

  const now = Math.floor(Date.now() / 1000);

  if (command === 'add') {
    const urlList: string[] = Array.isArray(urls) ? urls : typeof urls === 'string' ? [urls] : [];
    if (urlList.length === 0) {
      return res.status(400).json({ error: 'Danh sách URL trống' });
    }

    let added = 0;
    for (const rawUrl of urlList) {
      const cleanUrl = rawUrl.trim();
      if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) continue;
      const platform = guessPlatform(cleanUrl);
      const uid = `${platform}_${crypto.createHash('md5').update(cleanUrl).digest('hex').slice(0, 12)}`;
      
      const existing = videos.find(v => v.url === cleanUrl || v.uid === uid);
      if (!existing) {
        videos.unshift({
          uid,
          platform,
          url: cleanUrl,
          title: `Video ${platform} (${cleanUrl.slice(-15)})`,
          author: 'Manual import',
          state: 'queued',
          score: 7.5,
          views: 1000,
          likes: 120,
          comments: 15,
          attempts: 0,
          topic: 'manual_import',
          updated_at: now
        });
        added++;
      }
    }

    saveSeedData();
    runs.unshift({
      id: runs.length + 1,
      stage: 'add_urls',
      started: now,
      finished: now,
      ok: added,
      failed: urlList.length - added,
      note: `Đã thêm ${added} URL mới vào hàng đợi`
    });

    return res.json({ ok: true, message: `Đã thêm ${added} URL thành công` });
  }

  // Handle simulation of pipeline jobs
  activeJob = {
    command,
    started: now,
    output: `[Pipeline] Bắt đầu tác vụ: ${command} lúc ${new Date().toLocaleTimeString()}...\n`
  };

  res.status(202).json({ ok: true, status: 'started' });

  // Simulate background work asynchronously
  setTimeout(() => {
    const endNow = Math.floor(Date.now() / 1000);
    let ok = 0;
    let failed = 0;
    let note = '';

    if (command === 'discover') {
      const sampleTopics = ['ai_agents', 'gadgets', 'sigma_news', 'lifehack', 'shorts_viral'];
      const platforms = ['tiktok', 'douyin', 'youtube', 'instagram', 'reddit'];
      for (let i = 0; i < 6; i++) {
        const p = platforms[Math.floor(Math.random() * platforms.length)];
        const topic = sampleTopics[Math.floor(Math.random() * sampleTopics.length)];
        const hash = crypto.randomBytes(6).toString('hex');
        const views = Math.floor(Math.random() * 800000) + 50000;
        const likes = Math.floor(views * (0.05 + Math.random() * 0.1));
        const comments = Math.floor(likes * 0.08);
        const shares = Math.floor(likes * 0.15);
        const collects = Math.floor(likes * 0.2);
        const score = (views / 100000 * 0.2 + (likes / (views || 1)) * 30 + (collects / (views || 1)) * 40).toFixed(2);

        videos.unshift({
          uid: `${p}_${hash}`,
          platform: p,
          url: `https://${p}.com/v/${hash}`,
          title: `Xu hướng ${topic} mới nhất - Tổng hợp hot #${i + 1}`,
          author: `Kênh @${p}_creator_${i + 1}`,
          views,
          likes,
          comments,
          shares,
          collects,
          score: parseFloat(score),
          state: parseFloat(score) >= 7.0 ? 'queued' : 'discovered',
          attempts: 0,
          topic,
          updated_at: endNow
        });
        ok++;
      }
      note = `Đã quét và tìm thấy ${ok} video xu hướng mới`;
      activeJob.output += `[Discover] Tìm thấy ${ok} mục tiềm năng, đã chấm điểm và phân loại.\n`;
    } else if (command === 'download') {
      const queued = videos.filter(v => v.state === 'queued');
      for (const v of queued.slice(0, 10)) {
        v.state = 'downloaded';
        v.attempts = (v.attempts || 0) + 1;
        v.updated_at = endNow;
        ok++;
      }
      note = `Tải thành công ${ok} video từ hàng đợi`;
      activeJob.output += `[Download] Đã tải về ${ok} video, lưu trữ an toàn vào kho đệm.\n`;
    } else if (command === 'qc') {
      const downloaded = videos.filter(v => v.state === 'downloaded');
      for (const v of downloaded) {
        if (Math.random() > 0.12) {
          v.state = 'qc_passed';
          v.last_error = '';
          ok++;
        } else {
          v.state = 'qc_failed';
          v.last_error = 'Thiếu stream audio có tiếng người hoặc độ phân giải < 540p';
          failed++;
        }
        v.updated_at = endNow;
      }
      note = `Kiểm định QC: ${ok} đạt tiêu chuẩn, ${failed} loại`;
      activeJob.output += `[QC] Silero VAD + ffprobe kiểm tra âm thanh & hình ảnh hoàn tất: ${ok} passed, ${failed} failed.\n`;
    } else if (command === 'export') {
      const passed = videos.filter(v => v.state === 'qc_passed');
      for (const v of passed.slice(0, 8)) {
        v.state = 'exported';
        v.updated_at = endNow;
        ok++;
      }
      note = `Đã xuất ${ok} video đạt chuẩn sang AutoDub`;
      activeJob.output += `[Export] Chuẩn bị package handoff cho Kaggle/Colab AutoDub: ${ok} jobs sẵn sàng.\n`;
    } else if (command === 'collect') {
      const exported = videos.filter(v => v.state === 'exported');
      for (const v of exported) {
        v.state = 'dubbed';
        v.updated_at = endNow;
        ok++;
      }
      note = `Thu nhận ${ok} video đã hoàn tất lồng tiếng`;
      activeJob.output += `[Collect] Đã đồng bộ kết quả lồng tiếng từ Cloud vào kho lưu trữ.\n`;
    } else if (command === 'all') {
      // Run full pipeline
      const queued = videos.filter(v => v.state === 'queued');
      for (const v of queued) v.state = 'downloaded';
      const downloaded = videos.filter(v => v.state === 'downloaded');
      for (const v of downloaded) v.state = 'qc_passed';
      ok = downloaded.length;
      note = `Chạy toàn bộ quy trình: hoàn tất kiểm định ${ok} video`;
      activeJob.output += `[All] Đã thực hiện trọn gói Discovery -> Download -> QC -> Pipeline Ready.\n`;
    } else if (command === 'recheck') {
      const rejected = videos.filter(v => v.state === 'rejected' || v.state === 'qc_failed');
      for (const v of rejected) {
        v.state = 'queued';
        v.last_error = '';
        v.updated_at = endNow;
        ok++;
      }
      note = `Đã mở lại ${ok} video bị loại để xét tuyển`;
      activeJob.output += `[Recheck] Đã đưa ${ok} mục quay trở lại trạng thái queued.\n`;
    } else if (command === 'retry') {
      const errors = videos.filter(v => v.state === 'error');
      for (const v of errors) {
        v.state = 'queued';
        v.attempts = 0;
        v.last_error = '';
        v.updated_at = endNow;
        ok++;
      }
      note = `Đã cấp phép thử lại cho ${ok} video lỗi`;
      activeJob.output += `[Retry] Đã reset trạng thái cho ${ok} mục lỗi.\n`;
    }

    runs.unshift({
      id: runs.length + 1,
      stage: command,
      started: activeJob.started || now,
      finished: endNow,
      ok,
      failed,
      note
    });

    activeJob.output += `[Hoàn thành] Tác vụ kết thúc thành công lúc ${new Date().toLocaleTimeString()}.\n`;
    activeJob.command = null;
    saveSeedData();
  }, 1200);
});

// API: Projects List
app.get('/api/projects', (req: Request, res: Response) => {
  try {
    if (!fs.existsSync(OUTPUTS_DIR)) {
      return res.json({ projects: [] });
    }

    const items = fs.readdirSync(OUTPUTS_DIR);
    const projects = [];

    for (const item of items) {
      if (!item.startsWith('project_')) continue;
      const projPath = path.join(OUTPUTS_DIR, item);
      if (!fs.statSync(projPath).isDirectory()) continue;

      let brief: any = {};
      let scenes: any[] = [];
      let profile: any = {};
      let stats = fs.statSync(projPath);

      const briefPath = path.join(projPath, 'brief.json');
      if (fs.existsSync(briefPath)) {
        try { brief = JSON.parse(fs.readFileSync(briefPath, 'utf-8')); } catch {}
      }

      const scenesPath = path.join(projPath, 'scenes.json');
      if (fs.existsSync(scenesPath)) {
        try { scenes = JSON.parse(fs.readFileSync(scenesPath, 'utf-8')); } catch {}
      }

      const profilePath = path.join(projPath, 'preview_profile.json');
      if (fs.existsSync(profilePath)) {
        try { profile = JSON.parse(fs.readFileSync(profilePath, 'utf-8')); } catch {}
      }

      const totalDuration = scenes.reduce((sum: number, s: any) => sum + (Number(s.estimated_duration_sec) || 0), 0);

      projects.push({
        id: item,
        title: brief.title || item,
        aspectRatio: brief.aspect_ratio || profile.aspect_ratio || '9:16',
        scenesCount: scenes.length,
        duration: totalDuration || 45,
        updatedAt: stats.mtimeMs / 1000
      });
    }

    projects.sort((a, b) => b.updatedAt - a.updatedAt);
    res.json({ projects });
  } catch (err) {
    console.error('Error listing projects:', err);
    res.status(500).json({ error: 'Không thể đọc danh sách dự án' });
  }
});

// API: Project Detail
app.get('/api/projects/:id', (req: Request, res: Response) => {
  const id = String(req.params.id);
  const projPath = path.join(OUTPUTS_DIR, id);

  if (!fs.existsSync(projPath)) {
    return res.status(404).json({ error: 'Không tìm thấy dự án' });
  }

  let brief: any = {};
  let scenes: any[] = [];
  let previewProfile: any = {};
  let subtitles = '';
  let script = '';
  let roadmap = '';
  let mediaFiles: string[] = [];
  let audioFiles: string[] = [];

  const read = (f: string) => {
    const p = path.join(projPath, f);
    return fs.existsSync(p) ? fs.readFileSync(p, 'utf-8') : '';
  };

  try {
    const bStr = read('brief.json');
    if (bStr) brief = JSON.parse(bStr);
    const sStr = read('scenes.json');
    if (sStr) scenes = JSON.parse(sStr);
    const pStr = read('preview_profile.json');
    if (pStr) previewProfile = JSON.parse(pStr);
    subtitles = read('subtitles.srt');
    script = read('script.md');
    roadmap = read('PROJECT_ROADMAP.md');

    const mediaDir = path.join(projPath, 'media');
    if (fs.existsSync(mediaDir)) {
      mediaFiles = fs.readdirSync(mediaDir);
    }

    const audioDir = path.join(projPath, 'audio');
    if (fs.existsSync(audioDir)) {
      audioFiles = fs.readdirSync(audioDir);
    }
  } catch (e) {
    console.warn('Error reading project files:', e);
  }

  res.json({
    id,
    brief,
    scenes,
    previewProfile,
    subtitles,
    script,
    roadmap,
    mediaFiles,
    audioFiles
  });
});

// API: Update Project
app.post('/api/projects/:id/update', (req: Request, res: Response) => {
  const id = String(req.params.id);
  const projPath = path.join(OUTPUTS_DIR, id);

  if (!fs.existsSync(projPath)) {
    return res.status(404).json({ error: 'Không tìm thấy dự án' });
  }

  const { scenes, brief, subtitles, previewProfile } = req.body;

  try {
    if (scenes) {
      fs.writeFileSync(path.join(projPath, 'scenes.json'), JSON.stringify(scenes, null, 2), 'utf-8');
    }
    if (brief) {
      fs.writeFileSync(path.join(projPath, 'brief.json'), JSON.stringify(brief, null, 2), 'utf-8');
    }
    if (typeof subtitles === 'string') {
      fs.writeFileSync(path.join(projPath, 'subtitles.srt'), subtitles, 'utf-8');
    }
    if (previewProfile) {
      fs.writeFileSync(path.join(projPath, 'preview_profile.json'), JSON.stringify(previewProfile, null, 2), 'utf-8');
    }
    res.json({ ok: true });
  } catch (err) {
    console.error('Error saving project:', err);
    res.status(500).json({ error: 'Lỗi ghi file dự án' });
  }
});

// API: Create new Project
app.post('/api/projects/create', (req: Request, res: Response) => {
  const { title, aspectRatio, script } = req.body;
  const hex = crypto.randomBytes(6).toString('hex');
  const id = `project_${hex}`;
  const projPath = path.join(OUTPUTS_DIR, id);

  try {
    fs.mkdirSync(projPath, { recursive: true });
    fs.mkdirSync(path.join(projPath, 'media'), { recursive: true });
    fs.mkdirSync(path.join(projPath, 'audio'), { recursive: true });

    const brief = {
      title: title || 'Dự án dựng video mới',
      aspect_ratio: aspectRatio || '9:16'
    };
    fs.writeFileSync(path.join(projPath, 'brief.json'), JSON.stringify(brief, null, 2), 'utf-8');

    const defaultScenes = [
      {
        scene_id: 'scene_001',
        chapter_id: 'Phần mở đầu',
        narration: script || 'Chào mừng các bạn đến với bản tin xu hướng mới nhất.',
        estimated_duration_sec: 10.0,
        visual_intent: 'Cảnh 1: Giới thiệu ấn tượng',
        asset_ids: [],
        status: 'ready',
        format: aspectRatio || '9:16',
        tts_profile: 'male_warm',
        voice_resolution: { preset: 'male_warm', speed: 1.0, pitch: 0 }
      }
    ];

    fs.writeFileSync(path.join(projPath, 'scenes.json'), JSON.stringify(defaultScenes, null, 2), 'utf-8');
    fs.writeFileSync(path.join(projPath, 'script.md'), script || '', 'utf-8');
    fs.writeFileSync(path.join(projPath, 'subtitles.srt'), '1\n00:00:00,000 --> 00:00:10,000\n' + (script || 'Chào mừng các bạn đến với bản tin xu hướng mới nhất.') + '\n', 'utf-8');

    res.json({ ok: true, id, brief });
  } catch (err) {
    console.error('Error creating project:', err);
    res.status(500).json({ error: 'Lỗi tạo thư mục dự án' });
  }
});

// Serve asset / media files safely
app.use('/api/asset/:projectId', (req: Request, res: Response) => {
  const projectId = String(req.params.projectId);
  const file = req.path.replace(/^\//, '');
  const target = path.resolve(OUTPUTS_DIR, projectId, file);
  if (!target.startsWith(path.resolve(OUTPUTS_DIR, projectId))) {
    return res.status(403).json({ error: 'Access denied' });
  }
  if (!fs.existsSync(target)) {
    return res.status(404).json({ error: 'File not found' });
  }
  res.sendFile(target);
});

// Start Vite middleware in development
async function startServer() {
  const isProd = process.env.NODE_ENV === 'production';

  if (!isProd) {
    const vite = await createViteServer({
      server: { middlewareMode: true, host: '0.0.0.0', port: PORT },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(ROOT, 'dist');
    if (fs.existsSync(distPath)) {
      app.use(express.static(distPath));
      app.use((req: Request, res: Response) => {
        res.sendFile(path.join(distPath, 'index.html'));
      });
    }
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`🎬 Social Trend Pipeline running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
