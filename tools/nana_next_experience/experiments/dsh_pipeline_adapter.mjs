/** Explicit local invocation of dsh-see-now's original pipeline; no model calls.
 *
 * Usage: node dsh_pipeline_adapter.mjs /trusted/path/to/dsh-see-now < input.json
 * Input: {source_ref, rgb_path, width, height, fps, timestamps, max_frames_per_sheet}.
 * Caller supplies/validates source lineage and exact timestamps. This adapter
 * does not fetch media, qualify semantic observations, or persist results.
 */
import { open, readFile, stat } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const fail = (message) => { throw new Error(message); };
const root=process.argv[2];
if (!root) fail('trusted local dsh path required');
const chunks=[];let length=0;
for await (const chunk of process.stdin) {
  length+=chunk.length;if(length>1000000)fail('input too large');chunks.push(chunk);
}
const input=JSON.parse(Buffer.concat(chunks).toString('utf8'));
const {source_ref,rgb_path,width,height,fps,timestamps,max_frames_per_sheet}=input;
if (typeof source_ref!=='string'||source_ref.length<1||source_ref.length>128||
    typeof rgb_path!=='string'||!rgb_path.startsWith('/')||
    !Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||
    width*height>262144||!Number.isFinite(fps)||fps<=0||fps>120||
    !Array.isArray(timestamps)||timestamps.length<1||timestamps.length>1200||
    !Number.isInteger(max_frames_per_sheet)||max_frames_per_sheet<1||max_frames_per_sheet>16)
  fail('invalid bounded pipeline input');
let previous=-1;const exactByRounded=new Map();
for (const timestamp of timestamps) {
  if(!Number.isFinite(timestamp)||timestamp<0||timestamp>86400||timestamp<=previous)fail('invalid timestamps');
  // dsh log rounds to 0.01s. Reject collisions instead of inventing lineage.
  const rounded=Number(timestamp.toFixed(2));
  if(exactByRounded.has(rounded))fail('timestamps ambiguous at upstream log precision');
  exactByRounded.set(rounded,timestamp);previous=timestamp;
}
const frameBytes=width*height*3;
const file=await stat(rgb_path);
if(!file.isFile()||file.size!==frameBytes*timestamps.length||file.size>64*1024*1024)
  fail('RGB input does not match timestamps or bounds');
const {createPipeline}=await import(pathToFileURL(resolve(root,'src/pipeline.js')).href);
const pipeline=createPipeline({width,height,fps,maxFrames:max_frames_per_sheet});
const handle=await open(rgb_path,'r');
try {
  for(let i=0;i<timestamps.length;i++) {
    const buffer=Buffer.alloc(frameBytes);let bytes=0;
    while(bytes<frameBytes) {
      const result=await handle.read(buffer,bytes,frameBytes-bytes,null);
      if(!result.bytesRead)fail('truncated RGB input');
      bytes+=result.bytesRead;
    }
    pipeline.push({t:timestamps[i],buf:buffer});
  }
  pipeline.finish();
} finally { await handle.close(); }
const selected=pipeline.log.map(entry=>{
  const seconds=exactByRounded.get(entry.t);
  if(seconds===undefined)fail('upstream output cannot be mapped to an input timestamp');
  return {seconds,reason:entry.via};
});
console.log(JSON.stringify({schema_version:1,source_ref,input_frames:timestamps.length,selected,
  max_frames_per_sheet,stats:pipeline.stats,model_calls:0,
  qualification:'LOCAL_PIPELINE_OUTPUT_ONLY',
  caveat:'Frame limit is per sheet, not a total budget; source identity is caller supplied.'}));
