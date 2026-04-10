// ============================================================
// GLOBAL ALARM — custom audio or generated tone
// ============================================================

let defaultAudio = null;
let customAudio = null;
let customLoaded = false;
let customFailed = false;
let alarmCtx = null;
let alarmInterval = null;
let unlocked = false;

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

function getDefaultAudio() {
  if (!defaultAudio) {
    defaultAudio = new Audio(makeWavUrl());
    defaultAudio.volume = 0.8;
    defaultAudio.load();
  }
  return defaultAudio;
}

// Load custom audio from server
function loadCustomAudio() {
  if (customLoaded || customFailed) return;
  const a = new Audio('/api/v1/admin/alarm-audio/file?' + Date.now());
  a.volume = 0.8;
  a.addEventListener('canplaythrough', () => {
    customAudio = a;
    customLoaded = true;
    console.log('ALARM: Custom audio loaded');
  }, { once: true });
  a.addEventListener('error', () => {
    customFailed = true;
    console.log('ALARM: No custom audio, using default');
  }, { once: true });
  a.load();
}

// Try loading custom audio on init
if (typeof window !== 'undefined') {
  loadCustomAudio();
}

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
  } catch {}
}

export function playAlarmBeep() {
  // Pick custom audio if loaded, otherwise default
  const audio = customAudio || getDefaultAudio();
  try {
    audio.currentTime = 0;
    const p = audio.play();
    if (p && p.then) {
      p.then(() => { unlocked = true; })
       .catch(() => beepOscillator());
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
  if (alarmInterval) { clearInterval(alarmInterval); alarmInterval = null; }
}

export function reloadAlarmAudio() {
  customAudio = null;
  customLoaded = false;
  customFailed = false;
  loadCustomAudio();
}

// Unlock on user interaction
function tryUnlock() {
  if (unlocked) return;
  try {
    const a = getDefaultAudio();
    a.volume = 0.001; a.currentTime = 0;
    const p = a.play();
    if (p && p.then) p.then(() => { a.pause(); a.volume = 0.8; a.currentTime = 0; unlocked = true; }).catch(() => {});
  } catch {}
  try {
    if (!alarmCtx) alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (alarmCtx.state === 'suspended') alarmCtx.resume();
  } catch {}
}

if (typeof document !== 'undefined') {
  const evts = ['click','keydown','mousedown','touchstart','pointerdown'];
  const h = () => { tryUnlock(); if (unlocked) evts.forEach(e => document.removeEventListener(e, h, true)); };
  evts.forEach(e => document.addEventListener(e, h, { capture: true, passive: true }));
  window.addEventListener('load', () => setTimeout(tryUnlock, 500));
}
