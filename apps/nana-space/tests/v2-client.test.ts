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
