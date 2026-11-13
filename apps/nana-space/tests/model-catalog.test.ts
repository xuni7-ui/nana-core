import { expect, test } from "vitest";
import { readModelCatalog, mergeModelCatalog, catalogDisplayLimit } from "../src/data/model-catalog";

test("catalog completion remains unknown on older servers and capabilities are never inferred", () => {
  expect(readModelCatalog({models:["one"],capabilities:["VISION"]})).toEqual({models:["one"],truncated:true});
  expect(readModelCatalog({models:[],truncated:false,next_after_id:null})).toEqual({models:[],truncated:false});
  for(const value of [{models:["<script>"]},{models:Array(257).fill("one")},
    {models:["one"],truncated:false,next_after_id:"one"}, {models:["one"],truncated:true,next_after_id:"x&secret=y"}])
    expect(()=>readModelCatalog(value)).toThrow();
});

test("pages merge with deduplication and a revision binding; retries preserve prior results", () => {
  const first = mergeModelCatalog(undefined,{models:["z","a"],truncated:true,nextAfterId:"a"},3);
  const final = mergeModelCatalog(first,{models:["a","b"],truncated:false},3,"a");
  expect(final.models).toEqual(["a","b","z"]);expect(final.truncated).toBe(false);
  expect(()=>mergeModelCatalog(first,{models:["b"],truncated:false},4,"a")).toThrow(/配置已变化/);
  expect(()=>mergeModelCatalog(first,{models:["b"],truncated:false},3,"wrong")).toThrow();
  expect(first.models).toEqual(["a","z"]);
  expect(mergeModelCatalog(final,{models:["fresh"],truncated:false},4).models).toEqual(["fresh"]);
});

test("multi-page cycles and long duplicate-only catalogs cannot grow an unlimited list", () => {
  let previous = mergeModelCatalog(undefined,{models:["same"],truncated:true,nextAfterId:"one"},1);
  previous = mergeModelCatalog(previous,{models:["same"],truncated:true,nextAfterId:"two"},1,"one");
  expect(()=>mergeModelCatalog(previous,{models:["same"],truncated:true,nextAfterId:"one"},1,"two")).toThrow(/重复页面/);
  for(let i=0;previous.nextAfterId;i++)
    previous=mergeModelCatalog(previous,{models:["same"],truncated:true,nextAfterId:`cursor-${i}`},1,previous.nextAfterId);
  expect(previous.requestedAfterIds).toHaveLength(15);expect(previous.truncated).toBe(true);
  let large = mergeModelCatalog(undefined,{models:[],truncated:true,nextAfterId:"start"},1);
  for(let i=0;i<4;i++)large=mergeModelCatalog(large,{models:Array.from({length:256},(_,j)=>`model-${i}-${j}`),
    truncated:true,nextAfterId:`cursor-${i}`},1,large.nextAfterId);
  expect(large.models).toHaveLength(catalogDisplayLimit);expect(large.nextAfterId).toBeUndefined();
  expect(large.truncated).toBe(true);
});


test("catalog wait is optional and bounded; unknown metadata does not discard usable model choices", () => {
  for (const wait of [0, 1, 10000])
    expect(readModelCatalog({models:["one"],truncated:false,retry_after_ms:wait}).retryAfterMs).toBe(wait);
  for (const wait of [-1,10001,0.5,"1000",null]) {
    const result=readModelCatalog({models:["one"],truncated:false,retry_after_ms:wait});
    expect(result.retryAfterMs).toBeUndefined();expect(result.models).toEqual(["one"]);
  }
});
