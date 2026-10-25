import { parseInspectorSnapshot } from "./inspector";
import type { InspectorSnapshot } from "./contracts";
export interface CoreEnvelope<T> {
  contract: "nana-space-live/v1";
  subject_id: string;
  realm: "OWNED_DEVELOPMENT_ONLY";
  run_id: string;
  as_of_us: number;
  execution_authority: false;
  data: T;
}
export interface CoreData {
  inspector: InspectorSnapshot;
  runtime: {
    autonomy: string;
    provider: string;
    external_social_delivery: string;
  };
  capabilities: {
    read_only: true;
    send_input: boolean;
    max_message_characters: 2048;
    privacy: ["PROJECT"];
    memory_bodies: false;
    provider_settings: false;
    perception_capture: false;
    actions: false;
  };
}
export interface CoreReceipt {
  message_id: string;
  state: "REVIEWED" | "UNKNOWN";
  text: string | null;
  no_retry: true;
  provider_state?: string;
  render_state?: string;
  mode?: string;
  judgment?: string;
  intention?: string;
  message_memory_id?: string;
  raw_body_persisted?: boolean;
}
export class LiveError extends Error {
  constructor(public code: string) {
    super(code);
  }
}
async function transport(path: string, signal?: AbortSignal, body?: unknown) {
  let response: Response;
  try {
    response = await fetch(`/api/nana-space/v1/${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ?? AbortSignal.timeout(10000),
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new LiveError("CONNECTION_LOST");
  }
  const text = await response.text();
  if (text.length > 262144) throw new LiveError("RESPONSE_BOUND");
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new LiveError("INVALID_GATEWAY_RESPONSE");
  }
  if (!response.ok) {
    const code = (value as { code?: unknown })?.code;
    throw new LiveError(
      typeof code === "string" && /^[A-Z_]{1,80}$/.test(code)
        ? code
        : "GATEWAY_REJECTED",
    );
  }
  return value;
}
export function validateCoreEnvelope<T>(
  value: unknown,
  identity: string,
): CoreEnvelope<T> {
  if (!value || typeof value !== "object")
    throw new LiveError("INVALID_ENVELOPE");
  const row = value as Record<string, unknown>;
  if (
    row.contract !== "nana-space-live/v1" ||
    row.realm !== "OWNED_DEVELOPMENT_ONLY" ||
    row.execution_authority !== false
  )
    throw new LiveError("CONTRACT_OR_AUTHORITY_MISMATCH");
  if (row.subject_id !== identity)
    throw new LiveError("SUBJECT_IDENTITY_MISMATCH");
  if (
    typeof row.run_id !== "string" ||
    !/^[a-f0-9]{16}$/.test(row.run_id) ||
    typeof row.as_of_us !== "number" ||
    !Number.isSafeInteger(row.as_of_us) ||
    row.as_of_us < 0
  )
    throw new LiveError("INVALID_ENVELOPE");
  return {
    contract: "nana-space-live/v1",
    subject_id: identity,
    realm: "OWNED_DEVELOPMENT_ONLY",
    execution_authority: false,
    run_id: row.run_id,
    as_of_us: row.as_of_us,
    data: row.data as T,
  };
}
function receipt(value: unknown, identity: string, id: string, runId: string) {
  const envelope = validateCoreEnvelope<CoreReceipt>(value, identity);
  if (envelope.run_id !== runId)
    throw new LiveError("SESSION_GENERATION_CHANGED_NO_REPLAY");
  const r = envelope.data;
  if (
    !r ||
    r.message_id !== id ||
    !["REVIEWED", "UNKNOWN"].includes(r.state) ||
    r.no_retry !== true ||
    (r.text !== null && (typeof r.text !== "string" || r.text.length > 4096))
  )
    throw new LiveError("INVALID_RECEIPT");
  const clean: CoreReceipt = {
    message_id: id,
    state: r.state,
    no_retry: true,
    text: r.text,
  };
  for (const key of [
    "provider_state",
    "render_state",
    "mode",
    "judgment",
    "intention",
    "message_memory_id",
  ] as const) {
    const v = r[key];
    if (v !== undefined) {
      if (typeof v !== "string" || v.length > 128)
        throw new LiveError("INVALID_RECEIPT");
      clean[key] = v;
    }
  }
  if (r.raw_body_persisted !== undefined) {
    if (r.raw_body_persisted !== false)
      throw new LiveError("RETENTION_BOUNDARY_MISMATCH");
    clean.raw_body_persisted = false;
  }
  return { ...envelope, data: clean };
}
export const liveAdapter = {
  async login(password: string, identity: string) {
    const value = validateCoreEnvelope<{ authenticated: true }>(
      await transport("session", undefined, { password, subject_id: identity }),
      identity,
    );
    if (value.data?.authenticated !== true)
      throw new LiveError("SESSION_DENIED");
    return value;
  },
  async load(identity: string, signal?: AbortSignal) {
    const e = validateCoreEnvelope<CoreData>(
      await transport("snapshot", signal),
      identity,
    );
    const d = e.data,
      c = d?.capabilities;
    if (
      !d?.runtime ||
      !["RUNNING", "PAUSED"].includes(d.runtime.autonomy) ||
      d.runtime.provider !== "OFFLINE_NO_PROVIDER" ||
      d.runtime.external_social_delivery !== "DISABLED" ||
      c?.read_only !== true ||
      typeof c.send_input !== "boolean" ||
      c.max_message_characters !== 2048 ||
      c.actions !== false ||
      c.memory_bodies !== false ||
      c.provider_settings !== false ||
      c.perception_capture !== false ||
      !Array.isArray(c.privacy) ||
      c.privacy.length !== 1 ||
      c.privacy[0] !== "PROJECT"
    )
      throw new LiveError("INVALID_PROJECTION");
    return {
      ...e,
      data: {
        inspector: parseInspectorSnapshot(d.inspector, identity),
        runtime: {
          autonomy: d.runtime.autonomy,
          provider: d.runtime.provider,
          external_social_delivery: d.runtime.external_social_delivery,
        },
        capabilities: {
          read_only: true,
          send_input: c.send_input,
          max_message_characters: 2048,
          privacy: ["PROJECT"],
          memory_bodies: false,
          provider_settings: false,
          perception_capture: false,
          actions: false,
        },
      } as CoreData,
    };
  },
  async send(identity: string, runId: string, id: string, text: string) {
    return receipt(
      await transport("messages", undefined, {
        message_id: id,
        text,
        run_id: runId,
      }),
      identity,
      id,
      runId,
    );
  },
  async receipt(identity: string, id: string, runId: string) {
    if (!/^[A-Za-z0-9._:-]{1,64}$/.test(id))
      throw new LiveError("MESSAGE_ID_INVALID");
    return receipt(
      await transport(`receipts/${encodeURIComponent(id)}`),
      identity,
      id,
      runId,
    );
  },
};
