"""Offline anonymous language examples through default-off new-message bridge."""
import argparse,json
from dataclasses import asdict
from pathlib import Path
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.project_work.service import open_project_runtime
from nana_core.continuity.dialogue_shadow.bridge import ShadowBinding,NewExcerpt,NewMessageShadow

SAMPLES=(('vent','daily','今天只是吐槽一下，排队太久了。'),('help','project','请帮我排查这个项目问题。'),('share','daily','和你分享今天看到的晚霞。'),('refuse','private-topic','别再研究这个话题了。'),('retry','private-topic','请帮我看看这个。'),('ambiguous','daily','唉，这个项目啊。'),('quote','daily','如果有人说“不要研究”，你怎么看？'))

def run(root):
    rows=[];clock=VirtualClock()
    with open_project_runtime(root/'subject/self.db',clock) as r:
        now=r.clock.utc_now_us();binding=ShadowBinding(enabled=True,subject_id=r.identity_id,entity_id='project-user',scope='project-work',host_binding_id='manual-review',accepted_after_us=now,expires_at_us=now+60_000_000)
        bridge=NewMessageShadow(r,binding)
        for key,topic,text in SAMPLES:
            item=NewExcerpt(event_id=key,host_binding_id=binding.host_binding_id,subject_id=r.identity_id,entity_id='project-user',scope='project-work',occurred_at_us=now,topic=topic,text=text)
            review=asdict(bridge.review(item));rows.append(review)
        return {'source':'MANUALLY_AUTHORIZED_ANONYMOUS_EXAMPLES','reviews':rows,'real_qq_messages':0,'real_model_calls':0,'human_blind_review':'NOT_RUN','visible_delivery':'NOT_RUN','raw_excerpts_persisted':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.root.exists():p.error('fresh dedicated development root required')
    result=run(a.root);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'review_output':str(a.output),'real_qq_messages':0}))
if __name__=='__main__':main()
