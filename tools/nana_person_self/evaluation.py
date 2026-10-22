"""Descriptive measurements, never an automatic human-naturalness verdict."""
import re

def measure(text, *, mode):
    patterns={'ASSISTANT_VOICE':r'作为\s*(?:一个)?\s*(?:AI|人工智能)|as an AI',
        'META_SUMMARIZING':r'根据你的要求|我会按照|首先.{0,40}其次',
        'OVER_DISCLAIMER':r'我无法.{0,80}但我可以|我不能.{0,80}但我可以',
        'TRIAL_METAPHOR':r'试运行|trial period'}
    return {'characters':len(text),'sentences':len(re.findall(r'[。！？.!?]',text)),
        'pattern_counts':{k:len(re.findall(p,text,re.I)) for k,p in patterns.items()},
        'context_mode':mode,'patterns_are_diagnostic_not_banned_words':True,
        'human_naturalness':'NOT_RUN','unsupported_claims':'REQUIRES_SOURCE_AND_HUMAN_REVIEW'}
