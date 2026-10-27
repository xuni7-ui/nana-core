/** Bounded, read-only adaptation of the existing live/v2 Memory projection.
 * Drafts are user-provided suggestions, never Subject memories or lived events.
 */
export interface MemoryCard {
  id: string;
  text: string;
  source: string | null;
  type: string;
  epistemicKind: string;
  assessment: string;
  privacy: string;
  createdAt: number | null;
  topics: string[];
  relationships: string[];
}
export interface MemoryFilters {
  query?: string;
  type?: string;
  source?: string;
  topic?: string;
  relationship?: string;
  day?: string;
}
export interface ImportDraft {
  text: string;
  source: string;
  duplicate: boolean;
  provenance: "USER_PROVIDED_DRAFT";
}
export const MEMORY_IMPORT_MAX_BYTES = 256 * 1024;
export const MEMORY_IMPORT_MAX_ITEMS = 100;
const ownString = (value: unknown, max = 10000): string =>
  typeof value === "string" ? value.slice(0, max) : "";
const strings = (value: unknown) =>
  Array.isArray(value)
    ? value.filter((x): x is string => typeof x === "string").slice(0, 16)
    : [];
export function normalizeMemoryText(text: string) {
  return text.normalize("NFKC").replace(/\s+/g, " ").trim().toLocaleLowerCase();
}
export function memoryCards(rows: Record<string, unknown>[]): MemoryCard[] {
  const seen = new Set<string>();
  return rows.slice(0, 32).flatMap((row): MemoryCard[] => {
    // v2 is PUBLIC/PROJECT-only. A malformed row cannot expand envelope scope.
    if (!["PUBLIC", "PROJECT"].includes(String(row.privacy_class))) return [];
    const id = ownString(row.memory_id, 192);
    if (!id || seen.has(id)) return [];
    seen.add(id);
    const rawTime = row.created_at_us;
    const createdAt =
      typeof rawTime === "number" &&
      Number.isSafeInteger(rawTime) &&
      rawTime > 0 &&
      rawTime / 1000 <= 8640000000000000
        ? rawTime / 1000
        : null;
    return [
      {
        id,
        text: ownString(row.text),
        source: ownString(row.source_evidence_id, 192) || null,
        type: ownString(row.memory_type, 96) || "UNKNOWN",
        epistemicKind: ownString(row.epistemic_kind, 96) || "UNKNOWN",
        assessment: ownString(row.assessment, 96) || "UNKNOWN",
        privacy: ownString(row.privacy_class, 32) || "UNKNOWN",
        createdAt,
        topics: strings(row.topics),
        relationships: strings(row.relationship_refs),
      },
    ];
  });
}
export function filterMemories(
  cards: MemoryCard[],
  filters: MemoryFilters,
): MemoryCard[] {
  const needle = normalizeMemoryText(filters.query || "");
  return cards.filter(
    (card) =>
      (!needle ||
        normalizeMemoryText(
          [
            card.text,
            card.source || "",
            card.type,
            ...card.topics,
            ...card.relationships,
          ].join(" "),
        ).includes(needle)) &&
      (!filters.type || card.type === filters.type) &&
      (!filters.source || card.source === filters.source) &&
      (!filters.topic || card.topics.includes(filters.topic)) &&
      (!filters.relationship ||
        card.relationships.includes(filters.relationship)) &&
      (!filters.day || memoryDateKey(card.createdAt) === filters.day),
  );
}
export function memoryDateKey(createdAt: number | null) {
  if (createdAt === null) return "";
  const date = new Date(createdAt);
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}
export function memoryDay(createdAt: number | null) {
  return createdAt === null
    ? "时间未提供"
    : new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "long",
        day: "numeric",
      }).format(new Date(createdAt));
}
export function parseMemoryImport(
  filename: string,
  content: string,
  current: Pick<MemoryCard, "text">[],
): ImportDraft[] {
  if (new TextEncoder().encode(content).byteLength > MEMORY_IMPORT_MAX_BYTES)
    throw new Error("文件不能超过 256 KB。");
  if (!/\.(txt|md|json)$/i.test(filename))
    throw new Error("请选择 .txt、.md 或 .json 文件。");
  let rows: { text: string; source: string }[];
  if (/\.json$/i.test(filename)) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(content);
    } catch {
      throw new Error("JSON 格式不正确，尚未读取任何记忆。");
    }
    if (!Array.isArray(parsed))
      throw new Error("JSON 应为文本数组或含 text 字段的条目数组。");
    rows = parsed.map((entry) => {
      if (typeof entry === "string")
        return { text: entry, source: "用户选择的文件" };
      if (entry && typeof entry === "object" && !Array.isArray(entry)) {
        const row = entry as Record<string, unknown>;
        if (typeof row.text === "string")
          return {
            text: row.text,
            source: ownString(row.source, 192) || "用户选择的文件",
          };
      }
      throw new Error("每个条目必须是文本或包含 text 文本字段。");
    });
  } else {
    rows = content
      .split(/\n\s*\n/)
      .map((text) => ({ text, source: "用户选择的文件" }));
  }
  rows = rows.filter((row) => row.text.trim());
  if (!rows.length) throw new Error("文件没有可预览的文本。");
  if (rows.length > MEMORY_IMPORT_MAX_ITEMS)
    throw new Error("单次最多预览 100 条，请拆分文件。");
  if (rows.some((row) => row.text.length > 10000))
    throw new Error("单条文本不能超过 10000 字符。");
  const known = new Set(current.map((card) => normalizeMemoryText(card.text)));
  return rows.map((row) => {
    const normalized = normalizeMemoryText(row.text);
    const duplicate = known.has(normalized);
    known.add(normalized);
    return {
      text: row.text.trim(),
      source: row.source,
      duplicate,
      provenance: "USER_PROVIDED_DRAFT",
    };
  });
}
