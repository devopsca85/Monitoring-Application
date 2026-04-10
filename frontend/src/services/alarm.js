// --- Global Alarm Sound ---
// Uses HTML5 Audio as primary, Web Audio API as fallback
// Survives page navigation (imported as module singleton)

let alarmAudio = null;
let alarmCtx = null;
let alarmInterval = null;
let audioReady = false;

// Generate a WAV alarm tone in memory (no external files)
function generateAlarmWav() {
  const sampleRate = 8000;
  const duration = 0.8;
  const samples = Math.floor(sampleRate * duration);
  const buffer = new ArrayBuffer(44 + samples * 2);
  const view = new DataView(buffer);

  const w = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF');
  view.setUint32(4, 36 + samples * 2, true);
  w(8, 'WAVE'); w(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  w(36, 'data');
  view.setUint32(40, samples * 2, true);

  for (let i = 0; i < samples; i++) {
    const t = i / sampleRate;
    const freq = t < 0.25 ? 880 : t < 0.5 ? 660 : 880;
    const env = Math.min(1, (duration - t) * 4) * Math.min(1, t * 20);
    const val = Math.sin(2 * Math.PI * freq * t) * env * 0.6;
    view.setInt16(44 + i * 2, Math.max(-32768, Math.min(32767, val * 32767)), true);
  }

  return URL.createObjectURL(new Blob([buffer], { type: 'audio/wav' }));
}

// Try Web Audio API beep as fallback
function beepWithWebAudio() {
  try {
    if (!alarmCtx) {
      alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (alarmCtx.state === 'suspended') {
      alarmCtx.resume();
    }
    const osc = alarmCtx.createOscillator();
    const gain = alarmCtx.createGain();
    osc.connect(gain);
    gain.connect(alarmCtx.destination);
    osc.type = 'square';
    osc.frequency.setValueAtTime(880, alarmCtx.currentTime);
    osc.frequency.setValueAtTime(660, alarmCtx.currentTime + 0.2);
    osc.frequency.setValueAtTime(880, alarmCtx.currentTime + 0.4);
    gain.gain.setValueAtTime(0.4, alarmCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, alarmCtx.currentTime + 0.6);
    osc.start(alarmCtx.currentTime);
    osc.stop(alarmCtx.currentTime + 0.6);
    return true;
  } catch (e) {
    return false;
  }
}

function ensureAudio() {
  if (!alarmAudio) {
    alarmAudio = new Audio(generateAlarmWav());
    alarmAudio.volume = 0.8;
  }
  return alarmAudio;
}

export function playAlarmBeep() {
  console.log('ALARM: playAlarmBeep called');

  // Try HTML5 Audio first
  try {
    const audio = ensureAudio();
    audio.currentTime = 0;
    const promise = audio.play();
    if (promise) {
      promise.then(() => {
        console.log('ALARM: Audio played via HTML5 Audio');
        audioReady = true;
      }).catch((e) => {
        console.warn('ALARM: HTML5 Audio blocked, trying WebAudio:', e.message);
        beepWithWebAudio();
      });
    }
  } catch (e) {
    console.warn('ALARM: HTML5 Audio failed, trying WebAudio');
    beepWithWebAudio();
  }
}

export function startAlarmLoop() {
  if (alarmInterval) return;
  console.log('ALARM: Starting alarm loop');
  playAlarmBeep();
  alarmInterval = setInterval(playAlarmBeep, 5000);
}

export function stopAlarmLoop() {
  if (alarmInterval) {
    console.log('ALARM: Stopping alarm loop');
    clearInterval(alarmInterval);
    alarmInterval = null;
  }
}

// Unlock audio on first user interaction (browser requirement)
function unlock() {
  if (audioReady) return;
  console.log('ALARM: Unlocking audio via user gesture');
  try {
    const audio = ensureAudio();
    audio.volume = 0.01;
    audio.play().then(() => {
      audio.pause();
      audio.currentTime = 0;
      audio.volume = 0.8;
      audioReady = true;
      console.log('ALARM: Audio unlocked successfully');
    }).catch(() => {});
  } catch (e) {}

  // Also unlock Web Audio API
  try {
    if (!alarmCtx) alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (alarmCtx.state === 'suspended') alarmCtx.resume();
  } catch (e) {}
}

if (typeof document !== 'undefined') {
  ['click', 'keydown', 'touchstart', 'mousedown'].forEach((evt) => {
    document.addEventListener(evt, unlock, { once: false, capture: true });
  });
  // Also try to unlock after a short delay (some browsers allow it)
  setTimeout(() => unlock(), 1000);
}
