/** Bounded live frames, never a transcript cache or permission source. */
export class StreamError extends Error {
  constructor(public code: string) { super(code); }
}
export async function readChatFrames(
  body: ReadableStream<Uint8Array>,
  frame: (value: unknown) => boolean,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let pending = "", bytes = 0, frames = 0;
  try {
    while (true) {
      const item = await reader.read();
      if (item.done) throw new StreamError("STREAM_INTERRUPTED_VERIFY_ONLY");
      bytes += item.value.byteLength;
      if (bytes > 8388608) throw new StreamError("STREAM_RESPONSE_BOUND");
      pending += decoder.decode(item.value, { stream: true });
      let end: number;
      while ((end = pending.indexOf("\n")) >= 0) {
        const line = pending.slice(0, end); pending = pending.slice(end + 1);
        if (!line || line.length > 262144 || ++frames > 1024)
          throw new StreamError("STREAM_FRAME_BOUND");
        let value: unknown;
        try { value = JSON.parse(line); }
        catch { throw new StreamError("INVALID_STREAM"); }
        if (frame(value)) return; // a complete authenticated receipt is terminal
      }
      if (pending.length > 262144) throw new StreamError("STREAM_FRAME_BOUND");
    }
  } finally { await reader.cancel().catch(() => {}); }
}
