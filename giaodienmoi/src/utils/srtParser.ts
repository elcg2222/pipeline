import { SubtitleCue } from '../types';

export function parseSRT(data: string): SubtitleCue[] {
  if (!data) return [];
  const normalized = data.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
  const blocks = normalized.split(/\n\s*\n/);
  const cues: SubtitleCue[] = [];

  for (const block of blocks) {
    const lines = block.split('\n');
    if (lines.length < 2) continue;

    let timeLineIdx = 1;
    let id = parseInt(lines[0].trim(), 10);
    if (isNaN(id)) {
      // First line might be time itself
      timeLineIdx = 0;
      id = cues.length + 1;
    }

    const timeLine = lines[timeLineIdx] || '';
    const match = timeLine.match(/(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})/);
    if (!match) continue;

    const startStr = match[1];
    const endStr = match[2];
    const textLines = lines.slice(timeLineIdx + 1);
    const text = textLines.join('\n').trim();

    cues.push({
      id,
      start: timestampToSeconds(startStr),
      end: timestampToSeconds(endStr),
      startStr,
      endStr,
      text
    });
  }

  return cues;
}

export function timestampToSeconds(timestamp: string): number {
  const parts = timestamp.replace(',', '.').split(':');
  if (parts.length < 3) return 0;
  const hours = parseFloat(parts[0]);
  const minutes = parseFloat(parts[1]);
  const seconds = parseFloat(parts[2]);
  return hours * 3600 + minutes * 60 + seconds;
}

export function secondsToTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

export function cuesToSRT(cues: SubtitleCue[]): string {
  return cues
    .map((c, i) => `${i + 1}\n${secondsToTimestamp(c.start)} --> ${secondsToTimestamp(c.end)}\n${c.text}\n`)
    .join('\n');
}
