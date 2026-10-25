export class AdapterError extends Error {
  constructor(public readonly code: string, message: string) { super(message); this.name = 'AdapterError'; }
}
export function abortError() { return new DOMException('操作已取消', 'AbortError'); }
export function assertActive(signal?: AbortSignal) { if (signal?.aborted) throw abortError(); }
export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  assertActive(signal);
  return new Promise((resolve, reject) => {
    const cancel = () => { clearTimeout(timer); signal?.removeEventListener('abort', cancel); reject(abortError()); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', cancel); resolve(); }, ms);
    signal?.addEventListener('abort', cancel, { once: true });
  });
}
