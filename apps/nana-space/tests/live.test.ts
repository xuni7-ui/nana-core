import { it, expect, vi, afterEach } from "vitest";
import { liveAdapter, validateCoreEnvelope } from "../src/data/live";
const env = (data: unknown) => ({
  contract: "nana-space-live/v1",
  subject_id: "test-subject",
  realm: "OWNED_DEVELOPMENT_ONLY",
  run_id: "abcd1234abcd1234",
  as_of_us: 10,
  execution_authority: false,
  data,
});
afterEach(() => vi.unstubAllGlobals());
it("pins the same subject, version, generation and authority", () => {
  expect(() =>
    validateCoreEnvelope(
      { ...env({}), execution_authority: true },
      "test-subject",
    ),
  ).toThrow();
  expect(() => validateCoreEnvelope(env({}), "other")).toThrow();
  expect(() =>
    validateCoreEnvelope({ ...env({}), realm: "PRODUCTION" }, "test-subject"),
  ).toThrow();
  expect(
    validateCoreEnvelope(
      { ...env({}), private_dictionary: { secret: "not carried" } },
      "test-subject",
    ),
  ).not.toHaveProperty("private_dictionary");
});
it("does not retry dispatch after transport loss", async () => {
  const call = vi.fn().mockRejectedValue(new TypeError("disconnect"));
  vi.stubGlobal("fetch", call);
  await expect(
    liveAdapter.send("test-subject", "abcd1234abcd1234", "id", "hi"),
  ).rejects.toMatchObject({ code: "CONNECTION_LOST" });
  expect(call).toHaveBeenCalledTimes(1);
});
it("rejects stale generation and retained raw content in receipts", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            ...env({
              message_id: "id",
              state: "REVIEWED",
              no_retry: true,
              text: "Core response",
              raw_body_persisted: false,
            }),
            run_id: "1111111111111111",
          }),
        ),
      ),
  );
  await expect(
    liveAdapter.receipt("test-subject", "id", "abcd1234abcd1234"),
  ).rejects.toMatchObject({ code: "SESSION_GENERATION_CHANGED_NO_REPLAY" });
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify(
            env({
              message_id: "id",
              state: "REVIEWED",
              no_retry: true,
              text: "Core response",
              raw_body_persisted: true,
            }),
          ),
        ),
      ),
  );
  await expect(
    liveAdapter.receipt("test-subject", "id", "abcd1234abcd1234"),
  ).rejects.toMatchObject({ code: "RETENTION_BOUNDARY_MISMATCH" });
});
it("never turns errors or missing projection fields into a usable snapshot", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ code: "CORE_UNAVAILABLE" }), {
          status: 503,
        }),
      ),
  );
  await expect(liveAdapter.load("test-subject")).rejects.toMatchObject({
    code: "CORE_UNAVAILABLE",
  });
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(env({})))),
  );
  await expect(liveAdapter.load("test-subject")).rejects.toMatchObject({
    code: "INVALID_PROJECTION",
  });
});
