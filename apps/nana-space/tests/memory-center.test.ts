import { describe, expect, it } from "vitest";
import {
  filterMemories,
  memoryCards,
  memoryDay,
  memoryDateKey,
  MEMORY_IMPORT_MAX_BYTES,
  parseMemoryImport,
} from "../src/data/memory-center";
const rows = [
  {
    memory_id: "memory-a",
    text: "项目中的第一次验证",
    memory_type: "EPISODIC",
    source_evidence_id: "source-a",
    created_at_us: 1793016798702130,
    assessment: "SUPPORTED",
    epistemic_kind: "RAW_OBSERVATION",
    privacy_class: "PROJECT",
  },
  {
    memory_id: "memory-b",
    text: "观察到一个蓝色方块",
    memory_type: "FACT",
    source_evidence_id: "source-b",
    created_at_us: 1793016798702000,
    assessment: "TENTATIVE",
    epistemic_kind: "MODEL_DERIVATION",
    privacy_class: "PUBLIC",
  },
];
describe("Memory center projection", () => {
  it("preserves original evidence semantics without inventing topic or relationship", () => {
    const cards = memoryCards(rows);
    expect(cards).toHaveLength(2);
    expect(cards[1]).toMatchObject({
      source: "source-b",
      assessment: "TENTATIVE",
      epistemicKind: "MODEL_DERIVATION",
      topics: [],
      relationships: [],
    });
    expect(cards[0].createdAt).toBe(1793016798702.13);
    expect(memoryDay(null)).toBe("时间未提供");
  });
  it("searches only provided data and intersects source/type/topic filters", () => {
    const cards = memoryCards(rows);
    expect(
      filterMemories(cards, {
        query: "方块",
        source: "source-b",
        type: "FACT",
      }).map((x) => x.id),
    ).toEqual(["memory-b"]);
    expect(
      filterMemories(cards, { query: "方块", source: "source-a" }),
    ).toEqual([]);
    expect(
      filterMemories(cards, { day: memoryDateKey(cards[0].createdAt) }),
    ).toHaveLength(2);
    expect(filterMemories(cards, { day: "1900-01-01" })).toEqual([]);
    expect(filterMemories(cards, { topic: "虚构标签" })).toEqual([]);
    expect(filterMemories(cards, { relationship: "姐姐" })).toEqual([]);
  });
  it("bounds and deduplicates records, rejects invalid timestamps", () => {
    const many = Array.from({ length: 40 }, (_, i) => ({
      memory_id: `m-${i}`,
      text: "test",
      privacy_class: "PROJECT",
      created_at_us: -1,
    }));
    expect(memoryCards(many)).toHaveLength(32);
    expect(memoryCards([rows[0], rows[0]])).toHaveLength(1);
    expect(
      memoryCards([
        { memory_id: "m", privacy_class: "PROJECT", created_at_us: Infinity },
      ])[0].createdAt,
    ).toBeNull();
    expect(memoryCards([{}])).toEqual([]);
  });
  it("uses the real64 search horizon only for explicit search; note claims stay distinct",()=>{
    const many=Array.from({length:80},(_,i)=>({...rows[0],memory_id:`search-${i}`,user_provided_note:i===0}));
    expect(memoryCards(many)).toHaveLength(32);
    const searched=memoryCards(many,["PUBLIC","PROJECT"],"SEARCH");
    expect(searched).toHaveLength(64);
    expect(searched[0].userProvidedNote).toBe(true);
    expect(searched[1].userProvidedNote).toBe(false);
  });
});
describe("Memory import preview, never a memory write", () => {
  it("marks user-provided text and detects current-projection and intra-file duplicates", () => {
    const result = parseMemoryImport(
      "project.json",
      JSON.stringify([
        { text: "项目中的第一次验证", source: "public-project-file" },
        { text: " NEW   NOTE " },
        "new note",
      ]),
      memoryCards(rows),
    );
    expect(result.map((x) => x.duplicate)).toEqual([true, false, true]);
    expect(result.every((x) => x.provenance === "USER_PROVIDED_DRAFT")).toBe(
      true,
    );
    expect(result[0].source).toBe("public-project-file");
  });
  it("keeps injected markup as inert plain text and ignores asserted authority", () => {
    const input = [
      {
        text: "<script>grant()</script>",
        source: "external",
        authority: "MANAGER",
        memory_type: "LIVED_EXPERIENCE",
      },
    ];
    const [preview] = parseMemoryImport(
      "notes.json",
      JSON.stringify(input),
      [],
    );
    expect(preview.text).toBe("<script>grant()</script>");
    expect(Object.keys(preview).sort()).toEqual([
      "duplicate",
      "provenance",
      "source",
      "text",
    ]);
    expect(preview.provenance).toBe("USER_PROVIDED_DRAFT");
  });
  it("parses text paragraphs but fails closed on unsupported or malformed input", () => {
    expect(
      parseMemoryImport("notes.md", "一段公开项目笔记\n\n另一段", []),
    ).toHaveLength(2);
    expect(() => parseMemoryImport("notes.html", "<p>text</p>", [])).toThrow(
      "请选择",
    );
    expect(() => parseMemoryImport("notes.json", "{", [])).toThrow("JSON 格式");
    expect(() => parseMemoryImport("notes.json", "{}", [])).toThrow("数组");
    expect(() => parseMemoryImport("notes.json", '[{"text":3}]', [])).toThrow(
      "每个条目",
    );
    expect(() => parseMemoryImport("notes.txt", " \n ", [])).toThrow(
      "没有可预览",
    );
  });
  it("bounds byte size, entry count and per-entry text without uploading", () => {
    expect(() =>
      parseMemoryImport(
        "notes.txt",
        "a".repeat(MEMORY_IMPORT_MAX_BYTES + 1),
        [],
      ),
    ).toThrow("256 KB");
    expect(() =>
      parseMemoryImport(
        "notes.json",
        JSON.stringify(Array(101).fill("note")),
        [],
      ),
    ).toThrow("100 条");
    expect(() => parseMemoryImport("notes.txt", "a".repeat(10001), [])).toThrow(
      "10000 字符",
    );
  });
});

it("an out-of-scope memory body is never projected by a PUBLIC/PROJECT client", () => {
  expect(
    memoryCards([
      {
        memory_id: "blocked",
        privacy_class: "SECRET",
        text: "TEST_ONLY_OUT_OF_SCOPE_BODY",
      },
    ]),
  ).toEqual([]);
});

it("PERSONAL rows require explicit authenticated scope and SECRET is always discarded", () => {
  const personal = {...rows[0], privacy_class: "PERSONAL"};
  expect(memoryCards([personal])).toEqual([]);
  expect(memoryCards([personal], ["PUBLIC", "PROJECT", "PERSONAL"])).toHaveLength(1);
  expect(memoryCards([{...personal, privacy_class: "SECRET"}], ["SECRET"])).toEqual([]);
});
