import { Capacitor, registerPlugin } from "@capacitor/core";

interface LocalSpeech {
  listen(): Promise<{text: string; source: "DEVICE_LOCAL_ASR"; audio_uploaded: false}>;
  speak(options: {text: string}): Promise<{state: string; source: string}>;
  stop(): Promise<void>;
}
const native = registerPlugin<LocalSpeech>("NanaSpeech");
export async function transcribe(): Promise<string> {
  if (!Capacitor.isNativePlatform()) throw new Error("请使用手机键盘语音输入；浏览器不会自动启用联网识别。");
  const result = await native.listen();
  if (result.source !== "DEVICE_LOCAL_ASR" || result.audio_uploaded !== false || typeof result.text !== "string")
    throw new Error("未得到可确认的本地转写。");
  return result.text.slice(0, 2048);
}
export async function readAloud(text: string): Promise<void> {
  if (Capacitor.isNativePlatform()) { await native.speak({text: text.slice(0, 2048)}); return; }
  if (!("speechSynthesis" in window)) throw new Error("当前设备没有可用的本地朗读。");
  const voice = window.speechSynthesis.getVoices().find(v => v.localService && v.lang.startsWith("zh"));
  if (!voice) throw new Error("尚无中文本地语音，未改用联网服务。");
  await new Promise<void>((resolve, reject) => {
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 2048));
    utterance.voice = voice;
    utterance.onend = () => resolve();
    utterance.onerror = () => reject(new Error("本地朗读未完成。"));
    window.speechSynthesis.speak(utterance);
  });
}
export function stopSpeech(): void {
  if (Capacitor.isNativePlatform()) void native.stop().catch(() => {});
  else window.speechSynthesis?.cancel();
}
