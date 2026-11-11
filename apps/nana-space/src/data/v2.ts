import { Capacitor, registerPlugin } from "@capacitor/core";
import { readChatFrames, StreamError } from "./chat-stream";
export interface ChatProgress { state: "INTERPRETING"|"RENDERING"|"PROVISIONAL_MODEL_DRAFT"; text?: string; }
import type {
  Envelope,
  MessageRequest,
  MessageSequenceRequest,
  CommandRequest,
  HostRequest,
  HostConfirmation,
  ProviderConfigurationRequest,
  ProviderRuntimeBudgetRequest,
  MemoryNoteRequest,
  LanguageFeedbackRequest,
} from "./v2.generated";

export type LivePage =
  | "home"
  | "chat"
  | "memories"
  | "goals"
  | "journal"
  | "world"
  | "growth"
  | "devices"
  | "runtime"
  | "settings";
export const livePages: LivePage[] = [
  "home",
  "chat",
  "memories",
  "goals",
  "journal",
  "world",
  "growth",
  "devices",
  "runtime",
  "settings",
];
interface NativePort {
  addListener(event: "nanaChatProgress", listener: (frame: unknown) => void): Promise<{remove(): Promise<void>}>;
  login(options: { base: string; device_name: string }): Promise<unknown>;
  bindProviderCredential(options: { data: Record<string, unknown>; persistent?: boolean }): Promise<unknown>;
  bindPlatformCredential(options: { data: Record<string, unknown>; persistent?: boolean }): Promise<unknown>;
  status(): Promise<{
    paired: boolean;
    base?: string;
    subject_id?: string;
    lineage_binding?: string;
  }>;
  pair(options: {
    base: string;
    code: string;
    subject_id: string;
    device_name: string;
  }): Promise<unknown>;
  call(options: {
    operation: string;
    data: Record<string, unknown>;
  }): Promise<unknown>;
  logout(): Promise<{ cleared: boolean; server_revocation: string }>;
  notificationPermission(): Promise<{
    granted: boolean;
    background_push: string;
  }>;
  backgroundNotifications(options?: { enabled?: boolean }): Promise<{
    enabled: boolean; state: string; interval_minutes: number;
    private_body_in_notification: false; instant_push: false; physical_delivery_qualified: false;
  }>;
  notificationQuiet(options: { quiet: boolean }): Promise<void>;
  notifyForeground(options: {
    event_id: string;
    page: LivePage;
  }): Promise<void>;
  launchRoute(): Promise<{ page: LivePage }>;
}
export const nativePort = registerPlugin<NativePort>("NanaHost");
export const isNative = () => Capacitor.isNativePlatform();
export class V2Error extends Error {
  constructor(public code: string) {
    super(code);
  }
}
/** A note rejected before admission has no write to reconcile. Network loss does. */
export function noteFailureState(error: unknown, dispatched: boolean): "REJECTED"|"UNKNOWN" {
  if (!dispatched) return "REJECTED";
  const rejected = new Set(["SCOPE_DENIED","VALIDATION_ERROR","INVALID_REQUEST","STALE_EPOCH",
    "STALE_RUN_NO_REPLAY","REVISION_CONFLICT","IDEMPOTENCY_COLLISION","NATIVE_OPERATION_DENIED"]);
  return error instanceof V2Error && rejected.has(error.code) ? "REJECTED" : "UNKNOWN";
}
export function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new V2Error("INVALID_ENVELOPE");
  return value as Record<string, unknown>;
}
function integer(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}
export function envelope(
  value: unknown,
  subject?: string,
  lineage?: string,
): Envelope {
  const row = object(value);
  if (
    row.contract !== "nana-space-live/v2" ||
    !["OWNED_DEVELOPMENT_ONLY", "PRODUCTION_SINGLE_SUBJECT"].includes(
      String(row.realm),
    ) ||
    row.execution_authority !== false
  )
    throw new V2Error("CONTRACT_MISMATCH");
  if (
    typeof row.subject_id !== "string" ||
    !row.subject_id ||
    typeof row.lineage_binding !== "string" ||
    !/^[a-f0-9]{64}$/.test(row.lineage_binding)
  )
    throw new V2Error("INVALID_IDENTITY");
  if (
    (subject && row.subject_id !== subject) ||
    (lineage && row.lineage_binding !== lineage)
  )
    throw new V2Error("INVALID_IDENTITY");
  if (
    typeof row.run_generation !== "string" ||
    !/^[a-f0-9]{32}$/.test(row.run_generation) ||
    !integer(row.owner_epoch) ||
    !integer(row.as_of_us) ||
    !integer(row.revision) ||
    !integer(row.session_generation)
  )
    throw new V2Error("INVALID_ENVELOPE");
  if (
    ![
      "CURRENT",
      "NO_DATA",
      "BLOCKED_SCOPE",
      "UNKNOWN",
      "UNAVAILABLE",
      "STALE",
    ].includes(String(row.coverage))
  )
    throw new V2Error("INVALID_ENVELOPE");
  if (
    !Array.isArray(row.privacy_scope) ||
    row.privacy_scope.some((x) => !["PUBLIC", "PROJECT", "PERSONAL"].includes(String(x)))
  )
    throw new V2Error("SCOPE_DENIED");
  object(row.data);
  object(row.capabilities);
  if (
    !Array.isArray(row.source_refs) ||
    row.source_refs.length > 32 ||
    row.source_refs.some((x) => typeof x !== "string")
  )
    throw new V2Error("INVALID_ENVELOPE");
  return row as Envelope;
}

export class V2Client {
  private incarnation = 0;
  private csrf = "";
  private subject = "";
  private lineage = "";
  private realm = "";
  private generation = "";
  private async request(
    path: string,
    method = "GET",
    body?: unknown,
  ): Promise<unknown> {
    const incarnation = this.incarnation;
    let response: Response;
    try {
      response = await fetch("/api/nana-space/v2/" + path, {
        method,
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
          ...(method !== "GET" && this.csrf
            ? { "X-Nana-CSRF": this.csrf }
            : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(path === "messages/sequence" ? 2*4*600000+30000 : path === "messages" ? 1230000 : method === "GET" ? 10000 : 22000),
      });
    } catch {
      throw new V2Error(
        method === "GET" ? "CONNECTION_LOST" : "UNKNOWN_VERIFY_ONLY",
      );
    }
    const text = await response.text();
    if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
    if (text.length > 524288) throw new V2Error("RESPONSE_BOUND");
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new V2Error("INVALID_ENVELOPE");
    }
    if (!response.ok) {
      const code = object(parsed).code;
      throw new V2Error(
        typeof code === "string" && /^[A-Z_]{1,96}$/.test(code)
          ? code
          : "REQUEST_REJECTED",
      );
    }
    return parsed;
  }
  private async nativeCall(options: {
    operation: string;
    data: Record<string, unknown>;
  }): Promise<unknown> {
    const incarnation = this.incarnation;
    const result = await nativePort.call(options);
    if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
    return result;
  }
  private accept(value: unknown): Envelope {
    const result = envelope(
      value,
      this.subject || undefined,
      this.lineage || undefined,
    );
    if (this.realm && this.realm !== result.realm)
      throw new V2Error("INVALID_IDENTITY");
    this.realm = result.realm;
    this.subject = result.subject_id;
    this.lineage = result.lineage_binding;
    // A changed gateway/session requires UI reconciliation. No write is replayed.
    this.generation = result.run_generation;
    const csrf = object(result.data).csrf;
    if (!isNative() && typeof csrf === "string" && csrf.length >= 24)
      this.csrf = csrf;
    return result;
  }
  async login(password: string, subject: string): Promise<Envelope> {
    this.clear();
    this.subject = subject;
    const result = this.accept(
      await this.request("session", "POST", { password, subject_id: subject }),
    );
    const csrf = object(result.data).csrf;
    if (typeof csrf !== "string" || csrf.length < 24) {
      this.clear();
      throw new V2Error("INVALID_SESSION");
    }
    this.csrf = csrf;
    return this.bootstrap();
  }
  async loginDevice(base: string, deviceName: string): Promise<Envelope> {
    this.clear();
    return this.accept(await nativePort.login({ base, device_name: deviceName }));
  }
  async pair(
    base: string,
    code: string,
    subject: string,
    deviceName: string,
  ): Promise<Envelope> {
    this.clear();
    this.subject = subject;
    const incarnation = this.incarnation;
    const value = await nativePort.pair({
      base,
      code,
      subject_id: subject,
      device_name: deviceName,
    });
    if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
    return this.accept(value);
  }
  async bootstrap(): Promise<Envelope> {
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "bootstrap", data: {} })
        : await this.request("bootstrap"),
    );
  }
  async view(page: LivePage): Promise<Envelope> {
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "view", data: { page } })
        : await this.request("views/" + page),
    );
  }
  async events(cursor?: string): Promise<Envelope> {
    return this.accept(
      isNative()
        ? await this.nativeCall({
            operation: "events",
            data: { cursor: cursor || "" },
          })
        : await this.request(
            "events" + (cursor ? "?cursor=" + encodeURIComponent(cursor) : ""),
          ),
    );
  }
  async write(
    kind: "message" | "message.sequence" | "command" | "host.operation" | "providers.command" | "providers.runtime" | "memories.note" | "conversation.feedback",
    body:
      | MessageRequest
      | MessageSequenceRequest
      | CommandRequest
      | HostRequest
      | MemoryNoteRequest
      | LanguageFeedbackRequest
      | ProviderConfigurationRequest
      | ProviderRuntimeBudgetRequest,
  ): Promise<Envelope> {
    if (body.run_generation !== this.generation)
      throw new V2Error("STALE_RUN_NO_REPLAY");
    const path = {
      message: "messages",
      "message.sequence": "messages/sequence",
      command: "commands",
      "host.operation": "host/operations",
      "providers.command": "providers/commands",
      "providers.runtime": "providers/runtime",
      "memories.note": "memories/notes",
      "conversation.feedback": "conversation/feedback",
    }[kind];
    const result = isNative()
      ? await this.nativeCall({
          operation: kind,
          data: body as unknown as Record<string, unknown>,
        })
      : await this.request(path, "POST", body);
    return this.accept(result);
  }
  async streamMessage(body: MessageRequest, onProgress: (progress: ChatProgress) => void): Promise<Envelope> {
    if (body.run_generation !== this.generation) throw new V2Error("STALE_RUN_NO_REPLAY");
    const incarnation = this.incarnation;
    let sequence = 0, final: Envelope|undefined;
    const acceptFrame = (value: unknown): boolean => {
      if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
      const row = object(value);
      if (row.event === "error") throw new V2Error("STREAM_INTERRUPTED_VERIFY_ONLY");
      if (row.message_id !== body.client_request_id) throw new V2Error("INVALID_STREAM");
      const e = envelope(row.data, this.subject, this.lineage);
      if (e.run_generation !== body.run_generation || e.owner_epoch !== body.owner_epoch)
        throw new V2Error("STALE_RUN_NO_REPLAY");
      if (row.event === "receipt") {
        const receipt = object(e.data);
        if (receipt.receipt_id !== body.idempotency_key || receipt.client_request_id !== body.client_request_id
            || receipt.operation !== "MESSAGE" || receipt.no_retry !== true)
          throw new V2Error("INVALID_STREAM");
        final = this.accept(e); return true;
      }
      if (row.event !== "progress" || !integer(row.sequence) || row.sequence <= sequence || row.sequence > 1024)
        throw new V2Error("INVALID_STREAM");
      sequence = row.sequence;
      const progress = object(e.data);
      if (!["INTERPRETING","RENDERING","PROVISIONAL_MODEL_DRAFT"].includes(String(progress.state))
          || (progress.text !== undefined && (typeof progress.text !== "string" || [...progress.text].length > 4096)))
        throw new V2Error("INVALID_STREAM");
      onProgress({state: progress.state as ChatProgress["state"], ...(typeof progress.text === "string" ? {text:progress.text} : {})});
      return false;
    };
    if (isNative()) {
      let failed: unknown;
      const listener = await nativePort.addListener("nanaChatProgress", frame => {
        if (failed) return;
        try { acceptFrame(frame); } catch (error) { failed = error; }
      });
      try {
        const value = await this.nativeCall({operation:"message.stream",data:body as unknown as Record<string,unknown>});
        if (failed) throw failed;
        // The native final result uses the same original receipt envelope.
        acceptFrame({event:"receipt",message_id:body.client_request_id,data:value});
      } finally { await listener.remove(); }
    } else {
      let response: Response;
      try {
        response = await fetch("/api/nana-space/v2/messages/stream", {method:"POST",credentials:"same-origin",
          cache:"no-store",headers:{"Content-Type":"application/json","X-Nana-CSRF":this.csrf},
          body:JSON.stringify(body),signal:AbortSignal.timeout(1230000)});
      } catch { throw new V2Error("UNKNOWN_VERIFY_ONLY"); }
      if (!response.ok || !response.body) throw new V2Error("STREAM_INTERRUPTED_VERIFY_ONLY");
      if (!response.headers.get("Content-Type")?.startsWith("application/x-ndjson"))
        throw new V2Error("INVALID_STREAM");
      try { await readChatFrames(response.body,acceptFrame); }
      catch (error) {
        if (error instanceof V2Error) throw error;
        throw new V2Error(error instanceof StreamError ? error.code : "STREAM_INTERRUPTED_VERIFY_ONLY");
      }
    }
    if (!final) throw new V2Error("STREAM_INTERRUPTED_VERIFY_ONLY");
    return final;
  }
  async receipt(id: string): Promise<Envelope> {
    if (!/^[A-Za-z0-9._:-]{1,96}$/.test(id)) throw new V2Error("INVALID_ID");
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "receipt", data: { id } })
        : await this.request("receipts/" + id),
    );
  }
  async bindProviderCredential(data: Record<string, unknown>, persistent = false): Promise<Envelope> {
    if (!isNative()) throw new V2Error("NATIVE_SECRET_INPUT_REQUIRED");
    const incarnation = this.incarnation;
    const result = await nativePort.bindProviderCredential({ data, persistent });
    if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
    return this.accept(result);
  }
  async providerCredentials(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({ operation: "providers.credentials", data: {} })
      : await this.request("providers/credentials"));
  }
  async providerRuntime(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({operation:"providers.runtime.status",data:{}})
      : await this.request("providers/runtime"));
  }
  async providerModels(providerId: string, revision: number): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({operation: "providers.models", data: {provider_profile_id: providerId, profile_revision: revision}})
      : await this.request(`providers/models?provider_profile_id=${encodeURIComponent(providerId)}&profile_revision=${revision}`));
  }
  async searchMemories(query: string): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({operation:"memories.search", data:{query}})
      : await this.request("memories/search", "POST", {query}));
  }
  async revokeProviderCredential(data: Record<string, unknown>): Promise<Envelope> {
    if (!isNative()) throw new V2Error("NATIVE_SECRET_INPUT_REQUIRED");
    return this.accept(await this.nativeCall({ operation: "providers.credential.revoke", data: {...data, action: "REVOKE"} }));
  }
  async conversationHistory(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({ operation: "conversation.history", data: {} })
      : await this.request("conversation/history"));
  }
  async bilibiliHistory(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({ operation: "bilibili.history", data: {} })
      : await this.request("platform/bilibili"));
  }
  async platformStatus(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({operation: "platform.status", data: {}})
      : await this.request("platform/status"));
  }
  async bindPlatformCredential(data: Record<string, unknown>, persistent = false): Promise<Envelope> {
    if (!isNative()) throw new V2Error("NATIVE_SECRET_INPUT_REQUIRED");
    const incarnation = this.incarnation;
    const result = await nativePort.bindPlatformCredential({data, persistent});
    if (incarnation !== this.incarnation) throw new V2Error("SESSION_REVOKED");
    return this.accept(result);
  }
  async revokePlatformCredential(data: Record<string, unknown>): Promise<Envelope> {
    if (!isNative()) throw new V2Error("NATIVE_SECRET_INPUT_REQUIRED");
    return this.accept(await this.nativeCall({operation: "platform.credential.revoke", data: {...data, action: "REVOKE"}}));
  }
  async configurePlatform(data: Record<string, unknown>): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({operation: "platform.command", data})
      : await this.request("platform/commands", "POST", data));
  }
  async sharedLifeCandidates(): Promise<Envelope> {
    return this.accept(isNative()
      ? await this.nativeCall({ operation: "life.shares", data: {} })
      : await this.request("life/shares"));
  }
  async confirm(body: HostConfirmation): Promise<string> {
    const result = this.accept(
      isNative()
        ? await this.nativeCall({
            operation: "host.confirm",
            data: body as unknown as Record<string, unknown>,
          })
        : await this.request("host/confirmations", "POST", body),
    );
    const token = object(result.data).confirmation_id;
    if (typeof token !== "string" || token.length < 24)
      throw new V2Error("CONFIRMATION_REQUIRED");
    return token;
  }
  async backupStatus(): Promise<Envelope> {
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "backup.status", data: {} })
        : await this.request("backup/status"),
    );
  }
  async devices(): Promise<Envelope> {
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "devices", data: {} })
        : await this.request("devices"),
    );
  }
  async offer(deviceName: string, roles: string[]): Promise<Envelope> {
    const body = { device_name: deviceName, roles, lifetime_seconds: 120 };
    return this.accept(
      isNative()
        ? await this.nativeCall({ operation: "pair.offer", data: body })
        : await this.request("devices/offers", "POST", body),
    );
  }
  async revoke(deviceId: string): Promise<Envelope> {
    if (!/^[a-f0-9]{32}$/.test(deviceId)) throw new V2Error("INVALID_ID");
    return this.accept(
      isNative()
        ? await this.nativeCall({
            operation: "device.revoke",
            data: { device_id: deviceId },
          })
        : await this.request("devices/" + deviceId, "DELETE"),
    );
  }
  async logout(): Promise<void> {
    try {
      if (isNative()) await nativePort.logout();
      else if (this.subject) await this.request("session", "DELETE");
    } finally {
      this.clear();
    }
  }
  clear() {
    this.incarnation++;
    this.csrf = "";
    this.subject = "";
    this.lineage = "";
    this.realm = "";
    this.generation = "";
  }
}
export function writeBase(current: Envelope, id = crypto.randomUUID()) {
  return {
    client_request_id: id,
    idempotency_key: id,
    expected_revision: current.revision,
    run_generation: current.run_generation,
    owner_epoch: current.owner_epoch,
  };
}
