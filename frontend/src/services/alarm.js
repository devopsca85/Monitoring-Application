// ============================================================
// GLOBAL ALARM — plays sound even when user is on other pages
// Uses multiple strategies to ensure audio plays
// ============================================================

let alarmAudio = null;
let alarmCtx = null;
let alarmInterval = null;
let unlocked = false;

// Strategy 1: Generate WAV blob and play via <audio>
function makeWavUrl() {
  const sr = 8000, dur = 0.8, n = Math.floor(sr * dur);
  const buf = new ArrayBuffer(44 + n * 2);
  const v = new DataView(buf);
  const s = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  s(0,'RIFF'); v.setUint32(4,36+n*2,true); s(8,'WAVE'); s(12,'fmt ');
  v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
  v.setUint32(24,sr,true); v.setUint32(28,sr*2,true); v.setUint16(32,2,true);
  v.setUint16(34,16,true); s(36,'data'); v.setUint32(40,n*2,true);
  for (let i = 0; i < n; i++) {
    const t = i/sr, f = t<.25?880:t<.5?660:880;
    const e = Math.min(1,(dur-t)*4)*Math.min(1,t*20);
    v.setInt16(44+i*2, Math.round(Math.sin(2*Math.PI*f*t)*e*.6*32767), true);
  }
  return URL.createObjectURL(new Blob([buf], {type:'audio/wav'}));
}

let customAudioChecked = false;

function getAudio() {
  if (!alarmAudio) {
    // Try custom uploaded audio first
    if (!customAudioChecked) {
      customAudioChecked = true;
      const custom = new Audio('/api/v1/admin/alarm-audio/file');
      custom.volume = 0.8;
      custom.addEventListener('canplaythrough', () => {
        alarmAudio = custom;
      }, { once: true });
      custom.addEventListener('error', () => {
        // No custom audio — use generated WAV
        alarmAudio = new Audio(makeWavUrl());
        alarmAudio.volume = 0.8;
        alarmAudio.load();
      }, { once: true });
      custom.load();
      // Return generated wav for now until custom loads
      alarmAudio = new Audio(makeWavUrl());
      alarmAudio.volume = 0.8;
      alarmAudio.load();
    } else {
      alarmAudio = new Audio(makeWavUrl());
      alarmAudio.volume = 0.8;
      alarmAudio.load();
    }
  }
  return alarmAudio;
}

// Force reload custom audio (call after upload)
export function reloadAlarmAudio() {
  alarmAudio = null;
  customAudioChecked = false;
  getAudio();
}

// Strategy 2: Web Audio API oscillator
function beepOscillator() {
  try {
    if (!alarmCtx) alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (alarmCtx.state === 'suspended') alarmCtx.resume();
    const o = alarmCtx.createOscillator(), g = alarmCtx.createGain();
    o.connect(g); g.connect(alarmCtx.destination);
    o.type = 'square';
    const t = alarmCtx.currentTime;
    o.frequency.setValueAtTime(880,t); o.frequency.setValueAtTime(660,t+.2); o.frequency.setValueAtTime(880,t+.4);
    g.gain.setValueAtTime(.4,t); g.gain.exponentialRampToValueAtTime(.01,t+.6);
    o.start(t); o.stop(t+.6);
    return true;
  } catch { return false; }
}

// Play alarm — tries Audio element first, falls back to oscillator
export function playAlarmBeep() {
  // Try Audio element
  try {
    const a = getAudio();
    a.currentTime = 0;
    const p = a.play();
    if (p && p.then) {
      p.then(() => { unlocked = true; })
       .catch(() => { beepOscillator(); });
    }
  } catch {
    beepOscillator();
  }
}

export function startAlarmLoop() {
  if (alarmInterval) return;
  playAlarmBeep();
  alarmInterval = setInterval(playAlarmBeep, 4000);
}

export function stopAlarmLoop() {
  if (alarmInterval) {
    clearInterval(alarmInterval);
    alarmInterval = null;
  }
}

// Unlock audio on ANY user interaction — this is the key to making it work
function tryUnlock() {
  if (unlocked) return;
  try {
    const a = getAudio();
    // Play a tiny silent moment to unlock
    const origVol = a.volume;
    a.volume = 0.001;
    a.currentTime = 0;
    const p = a.play();
    if (p && p.then) {
      p.then(() => { a.pause(); a.volume = origVol; a.currentTime = 0; unlocked = true; }).catch(() => {});
    }
  } catch {}
  // Also unlock Web Audio
  try {
    if (!alarmCtx) alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (alarmCtx.state === 'suspended') alarmCtx.resume();
  } catch {}
}

// Attach to ALL interaction events, keep trying until unlocked
if (typeof document !== 'undefined') {
  const events = ['click','keydown','keyup','mousedown','mouseup','touchstart','touchend','pointerdown','scroll'];
  const handler = () => {
    tryUnlock();
    if (unlocked) {
      events.forEach(e => document.removeEventListener(e, handler, true));
    }
  };
  events.forEach(e => document.addEventListener(e, handler, { capture: true, passive: true }));
  // Also try after page load
  window.addEventListener('load', () => setTimeout(tryUnlock, 500));
}
