// --- Global Alarm Sound (works across all pages/tabs) ---

let alarmAudio = null;
let alarmInterval = null;
let audioUnlocked = false;

function generateAlarmWav() {
  const sampleRate = 8000;
  const duration = 0.8;
  const samples = Math.floor(sampleRate * duration);
  const buffer = new ArrayBuffer(44 + samples * 2);
  const view = new DataView(buffer);

  const writeStr = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + samples * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, 'data');
  view.setUint32(40, samples * 2, true);

  for (let i = 0; i < samples; i++) {
    const t = i / sampleRate;
    const freq = t < 0.25 ? 880 : t < 0.5 ? 660 : 880;
    const envelope = Math.min(1, (duration - t) * 4) * Math.min(1, t * 20);
    const sample = Math.sin(2 * Math.PI * freq * t) * envelope * 0.5;
    view.setInt16(44 + i * 2, Math.max(-32768, Math.min(32767, sample * 32767)), true);
  }

  const blob = new Blob([buffer], { type: 'audio/wav' });
  return URL.createObjectURL(blob);
}

function getAlarmAudio() {
  if (!alarmAudio) {
    alarmAudio = new Audio(generateAlarmWav());
    alarmAudio.volume = 0.7;
  }
  return alarmAudio;
}

export function playAlarmBeep() {
  try {
    const audio = getAlarmAudio();
    audio.currentTime = 0;
    audio.play().catch(() => {});
  } catch (e) {}
}

export function unlockAudio() {
  if (audioUnlocked) return;
  try {
    const audio = getAlarmAudio();
    audio.volume = 0;
    audio.play().then(() => {
      audio.pause();
      audio.volume = 0.7;
      audioUnlocked = true;
    }).catch(() => {});
  } catch (e) {}
}

export function startAlarmLoop() {
  if (alarmInterval) return;
  playAlarmBeep();
  alarmInterval = setInterval(playAlarmBeep, 5000);
}

export function stopAlarmLoop() {
  if (alarmInterval) {
    clearInterval(alarmInterval);
    alarmInterval = null;
  }
}

// Unlock audio on first user interaction
if (typeof document !== 'undefined') {
  ['click', 'keydown', 'touchstart'].forEach((evt) => {
    document.addEventListener(evt, unlockAudio, { once: true });
  });
}
