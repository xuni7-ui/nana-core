import { test, expect, vi, afterEach } from "vitest";
import { V2Client, envelope, V2Error } from "../src/data/v2";
const sample = () => ({
  contract: "nana-space-live/v2",
  realm: "OWNED_DEVELOPMENT_ONLY",
  execution_authority: false,
  subject_id: "test-subject",
  lineage_binding: "a".repeat(64),
  owner_epoch: 1,
  as_of_us: 1,
  revision: 0,
  session_generation: 1,
  run_generation: "b".repeat(32),
  coverage: "NO_DATA",
  privacy_scope: ["PUBLIC", "PROJECT"],
  source_refs: [],
  capabilities: {},
  data: {},
});
afterEach(() => vi.unstubAllGlobals());
test("late Web response after local logout is discarded before rebinding identity", async () => {
  let complete!: (x: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          complete = resolve;
        }),
    ),
  );
  const client = new V2Client();
  const pending = client.bootstrap();
  client.clear();
  complete(new Response(JSON.stringify(sample()), { status: 200 }));
  await expect(pending).rejects.toMatchObject({ code: "SESSION_REVOKED" });
});
test("authority injection, invalid scope and foreign subject fail envelope checks", () => {
  expect(envelope(sample()).subject_id).toBe("test-subject");
  expect(() => envelope({ ...sample(), execution_authority: true })).toThrow(
    V2Error,
  );
  expect(() => envelope({ ...sample(), privacy_scope: ["SECRET"] })).toThrow(
    "SCOPE_DENIED",
  );
  expect(() => envelope(sample(), "other")).toThrow("INVALID_IDENTITY");
});

test("new finite provider and backup routes use original session and unknown writes never retry", async () => {
  const request = vi.fn(async (_url: unknown, options?: RequestInit) => {
    if (options?.method === "POST")
      throw new TypeError("synthetic connection reset");
    return new Response(JSON.stringify(sample()), { status: 200 });
  });
  vi.stubGlobal("fetch", request);
  const client = new V2Client();
  await client.bootstrap();
  await client.backupStatus();
  expect(String(request.mock.calls.at(-1)?.[0])).toBe(
    "/api/nana-space/v2/backup/status",
  );
  await client.providerModels("catalog.main", 7);
  expect(String(request.mock.calls.at(-1)?.[0])).toBe(
    "/api/nana-space/v2/providers/models?provider_profile_id=catalog.main&profile_revision=7",
  );
  await expect(
    client.write("providers.command", {
      client_request_id: "new",
      idempotency_key: "new",
      expected_revision: 0,
      run_generation: "b".repeat(32),
      owner_epoch: 1,
      command: {
        operation: "DISABLE_PROVIDER",
        target_id: "provider.a",
        expected_revision: 5,
      },
    }),
  ).rejects.toMatchObject({ code: "UNKNOWN_VERIFY_ONLY" });
  expect(
    request.mock.calls.filter((x) =>
      String(x[0]).includes("providers/commands"),
    ),
  ).toHaveLength(1);
});

test("living projections use scoped GET routes and browser credential mutations never reach fetch", async () => {
  const request = vi.fn(async (_url: unknown) => new Response(JSON.stringify(sample()), {status: 200}));
  vi.stubGlobal("fetch", request);
  const client = new V2Client();
  await client.conversationHistory();
  await client.bilibiliHistory();
  await client.sharedLifeCandidates();
  await client.providerCredentials();
  expect(request.mock.calls.map(call => String(call[0]))).toEqual([
    "/api/nana-space/v2/conversation/history", "/api/nana-space/v2/platform/bilibili",
    "/api/nana-space/v2/life/shares", "/api/nana-space/v2/providers/credentials",
  ]);
  await expect(client.bindProviderCredential({provider_profile_id: "provider.a"}, true)).rejects.toMatchObject({code: "NATIVE_SECRET_INPUT_REQUIRED"});
  await expect(client.revokeProviderCredential({provider_profile_id: "provider.a"})).rejects.toMatchObject({code: "NATIVE_SECRET_INPUT_REQUIRED"});
  expect(request).toHaveBeenCalledTimes(4);
});

test("additive PERSONAL envelope is accepted while SECRET remains forbidden", () => {
  expect(envelope({...sample(), privacy_scope: ["PUBLIC", "PROJECT", "PERSONAL"]}).privacy_scope).toContain("PERSONAL");
  expect(() => envelope({...sample(), privacy_scope: ["PUBLIC", "SECRET"]})).toThrow("SCOPE_DENIED");
});
