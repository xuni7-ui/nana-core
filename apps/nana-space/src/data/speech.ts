import { Capacitor, registerPlugin } from "@capacitor/core";

interface LocalSpeech {
  listen(): Promise<{text: string; source: "DEVICE_LOCAL_ASR"; audio_uploaded: false}>;
  speak(options: {text: string}): Promise<{state: string; source: string}>;
  stop(): Promise<void>;
}
const native = registerPlugin<LocalSpeech>("NanaSpeech");
let cancelLocalSpeech: (() => void) | undefined;
export async function transcribe(): Promise<string> {
  if (!Capacitor.isNativePlatform()) throw new Error("请使用手机键盘语音输入；浏览器不会自动启用联网识别。");
  const result = await native.listen();
  if (result.source !== "DEVICE_LOCAL_ASR" || result.audio_uploaded !== false || typeof result.text !== "string")
    throw new Error("未得到可确认的本地转写。");
  return result.text.slice(0, 2048);
}
export async function readAloud(text: string): Promise<void> {
  if (Capacitor.isNativePlatform()) {
    const result = await native.speak({text: text.slice(0, 2048)});
    if (result.source !== "DEVICE_LOCAL_TTS" || result.state !== "PLAYBACK_FINISHED") throw new Error("朗读结果尚未确认。");
    return;
  }
  if (!("speechSynthesis" in window)) throw new Error("当前设备没有可用的本地朗读。");
  const voice = window.speechSynthesis.getVoices().find(v => v.localService && v.lang.startsWith("zh"));
  if (!voice) throw new Error("尚无中文本地语音，未改用联网服务。");
  stopSpeech();
  await new Promise<void>((resolve, reject) => {
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 2048));
    let settled = false;
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (cancelLocalSpeech === cancel) cancelLocalSpeech = undefined;
      utterance.onend = null;
      utterance.onerror = null;
      error ? reject(error) : resolve();
    };
    const cancel = () => finish(new Error("本地朗读已停止。"));
    const timer = setTimeout(() => { finish(new Error("本地朗读超时。")); window.speechSynthesis.cancel(); }, 120000);
    cancelLocalSpeech = cancel;
    utterance.voice = voice;
    utterance.onend = () => finish();
    utterance.onerror = () => finish(new Error("本地朗读未完成。"));
    try { window.speechSynthesis.speak(utterance); }
    catch { finish(new Error("本地朗读无法启动。")); }
  });
}
export function stopSpeech(): void {
  if (Capacitor.isNativePlatform()) void native.stop().catch(() => {});
  else { cancelLocalSpeech?.(); window.speechSynthesis?.cancel(); }
}
