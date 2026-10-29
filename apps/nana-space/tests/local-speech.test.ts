import { afterEach, expect, test, vi } from "vitest";
vi.mock("@capacitor/core", () => ({Capacitor: {isNativePlatform: () => false}, registerPlugin: () => ({})}));
import { readAloud, stopSpeech } from "../src/data/speech";

afterEach(() => { stopSpeech(); vi.unstubAllGlobals(); });
function localVoice() {
  const speak = vi.fn(), cancel = vi.fn();
  vi.stubGlobal("window", {speechSynthesis: {getVoices: () => [{localService: true, lang: "zh-CN"}], speak, cancel}});
  vi.stubGlobal("SpeechSynthesisUtterance", class {text: string; constructor(text: string) {this.text = text;} });
  return {speak, cancel};
}
test("stopping local speech settles the pending job even when the browser emits no end event", async () => {
  const {speak, cancel} = localVoice();
  const pending = readAloud("PROJECT sourced wording");
  const rejected = expect(pending).rejects.toThrow("已停止");
  expect(speak).toHaveBeenCalledTimes(1);
  stopSpeech();
  await rejected;
  expect(cancel).toHaveBeenCalled();
});
test("a network-only voice is never selected as a fallback", async () => {
  const speak = vi.fn();
  vi.stubGlobal("window", {speechSynthesis: {getVoices: () => [{localService: false, lang: "zh-CN"}], speak, cancel: vi.fn()}});
  await expect(readAloud("PROJECT text")).rejects.toThrow("未改用联网服务");
  expect(speak).not.toHaveBeenCalled();
});
