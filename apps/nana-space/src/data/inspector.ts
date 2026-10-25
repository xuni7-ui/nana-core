import type { InspectorItem, InspectorSnapshot } from "./contracts";
import { AdapterError } from "./errors";
export const MAX_INSPECTOR_BYTES = 2 * 1024 * 1024;
const SECTIONS = new Set([
  "runtime",
  "goals",
  "activities",
  "concerns",
  "needs",
  "affect",
  "relationship",
  "interests",
  "suppressed_deferred",
  "decisions",
  "experience",
  "provenance",
  "authority",
  "unknown",
  "provider",
  "queue",
  "source_lifecycle",
  "health",
  "private_intents",
  "skills",
  "world",
  "learning",
]);
function fail(code = "INSPECTOR_INVALID"): never {
  throw new AdapterError(
    code,
    "快照格式或权限边界不符合 Inspector V1。未导入任何内容。",
  );
}
function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    return fail();
  return value as Record<string, unknown>;
}
function token(value: unknown, max: number): string {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > max ||
    /[\u0000-\u001f\u007f]/.test(value)
  )
    return fail();
  return value;
}
function integer(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0)
    return fail();
  return value;
}
function item(value: unknown): InspectorItem {
  const row = record(value);
  const state = token(row.state, 64);
  if (!/^[A-Z][A-Z0-9_]{0,63}$/.test(state)) return fail();
  const refs = row.source_memory_ids ?? [];
  if (!Array.isArray(refs) || refs.length > 32) return fail("INSPECTOR_BOUND");
  return {
    category: token(row.category, 96),
    reference: token(row.reference, 256),
    state,
    record_id: row.record_id == null ? null : token(row.record_id, 128),
    as_of_us: row.as_of_us == null ? null : integer(row.as_of_us),
    source_memory_ids: refs.map((ref) => token(ref, 128)),
  };
}
/** Projects the existing Core DTO. Unknown fields never enter UI state.
 * User-selected local snapshot import is not authentication or live connection. */
export function parseInspectorSnapshot(
  input: unknown,
  expectedIdentity?: string,
): InspectorSnapshot {
  let value: unknown = input;
  if (typeof input === "string") {
    if (new TextEncoder().encode(input).byteLength > MAX_INSPECTOR_BYTES)
      return fail("INSPECTOR_BOUND");
    try {
      value = JSON.parse(input);
    } catch {
      return fail("INSPECTOR_JSON_INVALID");
    }
  }
  const root = record(value);
  if (root.schema_version !== 1) return fail("INSPECTOR_SCHEMA_UNSUPPORTED");
  if (
    root.derived !== true ||
    root.read_only !== true ||
    root.execution_authority !== false ||
    root.coverage !== "BOUNDED_METADATA_ONLY" ||
    root.governance_visibility !== "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE"
  )
    return fail("INSPECTOR_PERMISSION_DENIED");
  const identity = token(root.identity_id, 128);
  if (expectedIdentity !== undefined && identity !== expectedIdentity)
    return fail("SUBJECT_IDENTITY_MISMATCH");
  const rawSections = record(root.sections);
  if (Object.keys(rawSections).length > 32) return fail("INSPECTOR_BOUND");
  const sections: Record<string, InspectorItem[]> = Object.create(null);
  for (const [key, rows] of Object.entries(rawSections)) {
    if (!SECTIONS.has(key)) continue;
    if (!Array.isArray(rows) || rows.length > 32)
      return fail("INSPECTOR_BOUND");
    sections[key] = rows.map(item);
  }
  let resources: Record<string, number> | null = null;
  if (root.resources != null) {
    const raw = record(root.resources);
    resources = {};
    for (const key of ["VmRSS", "Threads"])
      if (raw[key] !== undefined) resources[key] = integer(raw[key]);
  }
  return {
    schema_version: 1,
    derived: true,
    read_only: true,
    identity_id: identity,
    as_of_us: integer(root.as_of_us),
    coverage: "BOUNDED_METADATA_ONLY",
    governance_visibility: "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE",
    sections,
    resources,
    execution_authority: false,
  };
}
export function inspectorFileBound(file: Pick<File, "size">) {
  if (file.size > MAX_INSPECTOR_BYTES) fail("INSPECTOR_BOUND");
}
