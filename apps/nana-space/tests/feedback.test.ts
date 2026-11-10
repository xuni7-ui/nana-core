import {describe,it,expect} from 'vitest';
import {createHash} from 'node:crypto';
import {languageFeedbackSample,languageFeedbackResponseBinding,reviewableResponse} from '../src/data/feedback';

describe('source-bound long reply feedback',()=>{
  for (const reply of ['SYNTHETIC '+('full response. '.repeat(200)),'🌙'.repeat(3000)]) {
    it(`hashes complete UTF-8 response and keeps the legacy sample small (${reply.startsWith('🌙')?'unicode':'ascii'})`,async()=>{
      const sample=languageFeedbackSample({id:'turn',input:'SYNTHETIC question',state:'VERIFIED',exchangeId:'exchange',reply},'review','TOO_VERBOSE',1);
      expect(sample.candidate_response).toBe('DEPENDENT_RECORD_BODY');
      expect(sample.reason_tags).toEqual(['TOO_VERBOSE']);
      expect(await languageFeedbackResponseBinding(reply)).toEqual({response_sha256:createHash('sha256').update(reply,'utf8').digest('hex')});
      expect(reviewableResponse(reply)).toBe(false);
      expect(reviewableResponse(reply,true)).toBe(true);
    });
  }
  it('preserves short codepoint-bound samples and rejects beyond original reply bound',async()=>{
    const reply='🌙'.repeat(2048);
    expect(reviewableResponse(reply)).toBe(true);
    expect(await languageFeedbackResponseBinding(reply)).toEqual({});
    expect(languageFeedbackSample({id:'turn',input:'SYNTHETIC',state:'VERIFIED',exchangeId:'exchange',reply},'review','NATURAL',1).candidate_response).toBe(reply);
    expect(reviewableResponse('x'.repeat(16385),true)).toBe(false);
    await expect(languageFeedbackResponseBinding('x'.repeat(16385))).rejects.toThrow('FEEDBACK_TURN_UNAVAILABLE');
  });
});
