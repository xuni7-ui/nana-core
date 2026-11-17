/** Test actual dsh take/restore in memory; simulated outcomes, no delivery. */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const root=process.argv[2];if(!root)throw Error('trusted local dsh path required');
const {createPipeline}=await import(pathToFileURL(resolve(root,'src/pipeline.js')).href);
const width=160,height=90,size=width*height*3;
const pipe=createPipeline({width,height,fps:4,maxFrames:2,queueDepth:1});
let cursor=0;
function feedToPending() {
  while(pipe.pending===0&&cursor<120){
    const value=Math.floor(cursor/4)%2===0?0:255;
    pipe.push({t:cursor/4,buf:Buffer.alloc(size,value)});cursor++;
  }
  if(pipe.pending!==1)throw Error('synthetic stream produced no queued sheet');
}
feedToPending();const first=pipe.take();
if(!first)throw Error('no first sheet');
// Failure before external dispatch: restoring a locally held sheet is safe.
const restoredEmpty=pipe.restore(first);
const originalAgain=pipe.take();
if(!originalAgain)throw Error('restore into empty queue was not observable');
// A newer sheet occupies the queue while the older sheet is in flight.
feedToPending();const restoreWithNewer=pipe.restore(originalAgain);
const newer=pipe.take();if(!newer)throw Error('newer sheet disappeared');
// Simulated UNKNOWN: do not call restore or issue any external operation.
const pendingAfterUnknown=pipe.pending;
console.log(JSON.stringify({restored_empty:restoredEmpty,
  restored_same_sheet:originalAgain===first,restore_with_newer:restoreWithNewer,
  old_from:first.from,new_from:newer.from,pending_after_unknown:pendingAfterUnknown,
  unknown_state:'UNKNOWN_NOT_RETRIED',model_calls:0,external_sends:0,
  qualification:'SYNTHETIC_IN_PROCESS_ONLY'}));
