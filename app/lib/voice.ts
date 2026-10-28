// Microphone → WAV (mono PCM16, 16 kHz), the only format the transcription API accepts. Nothing is stored:
// the WAV goes to /api/transcribe and is dropped.

const RATE = 16000;
const MAX_SECONDS = 55; // the core accepts ~60 s

export type Recording = { stop: () => Promise<Blob>; cancel: () => void };

export async function startRecording(onAutoStop?: () => void): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  const ctx = new AudioContext();
  const source = ctx.createMediaStreamSource(stream);
  // ScriptProcessor: deprecated but available everywhere (Safari included) and needs no extra module file
  const node = ctx.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let length = 0;
  node.onaudioprocess = (e) => {
    const data = new Float32Array(e.inputBuffer.getChannelData(0));
    chunks.push(data);
    length += data.length;
    if (length > ctx.sampleRate * MAX_SECONDS) onAutoStop?.();
  };
  source.connect(node);
  node.connect(ctx.destination);
  const close = () => {
    node.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };
  return {
    stop: async () => {
      close();
      const all = new Float32Array(length);
      let o = 0;
      for (const c of chunks) {
        all.set(c, o);
        o += c.length;
      }
      return encodeWav(resample(all, ctx.sampleRate, RATE), RATE);
    },
    cancel: close,
  };
}

function resample(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    // average the source samples that fall in this output sample (a simple low-pass for downsampling)
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = end > start ? sum / (end - start) : 0;
  }
  return out;
}

function encodeWav(samples: Float32Array, rate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const str = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  str(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

/** Spoken answer with the browser's own speech synthesis (nothing leaves the phone). */
export function speak(text: string, lang: "es" | "en") {
  if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/DEMO-0*(\d+)/g, "demo $1"));
  u.lang = lang === "en" ? "en-US" : "es-ES";
  u.rate = 1.05;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
}
