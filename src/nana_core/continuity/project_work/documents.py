"""Bounded document navigation, not CommonMark or executable plugin parsing.

Production workflow and oracle are distinct implementations. Grammar deliberately
covers column-zero ATX headings with space and triple-backtick fenced blocks.
No target fetch, HTML execution or filesystem access occurs in either evaluator.
"""
import re
from ...contracts import CoreError


def outline(method,data):
    if method not in {f'MD_OUTLINE_{n}' for n in range(1,7)}:raise CoreError('DOCUMENT_METHOD_UNSUPPORTED')
    if type(data)!=dict or set(data)!={'filename','sha256','source'} or type(data['source'])!=str or len(data['source'].encode())>6144:raise CoreError('DOCUMENT_SOURCE_CONTRACT')
    depth=int(method[-1]);rows=[];fenced=False
    for n,line in enumerate(data['source'].split('\n'),1):
        if line.startswith('```'):fenced=not fenced;continue
        level=len(line)-len(line.lstrip('#'))
        if not fenced and 1<=level<=depth and line[level:level+1]==' ':
            rows.append({'level':level,'title':line[level:].strip(),'line':n})
    return rows


def expected_outline(data):
    """Independent anchored-regex oracle, never candidate output/self-report."""
    source=data['source'];rows=[]
    fences=list(re.finditer(r'^```[^\n]*(?:\n|$)',source,re.M))
    for match in re.finditer(r'^(#{1,6}) ([^\n]*)',source,re.M):
        if sum(f.start()<match.start() for f in fences)%2:continue
        rows.append({'level':len(match[1]),'title':match[2].strip(),'line':source.count('\n',0,match.start())+1})
    return rows


class PracticeRecipeProposer:
    """Finite workflow-parameter synthesis from practice only, not algorithm invention.

The allowed depth family is host reviewed; a candidate instantiates the smallest
recipe explaining practice. Heldout/transfer cases never enter this interface.
"""
    def propose_method(self,problem):
        if problem.domain!='markdown-outline':return problem.hypotheses[0]
        for candidate in problem.hypotheses:
            if all(outline(candidate,c.data)==c.expected for c in problem.practice):return candidate
        raise CoreError('DOCUMENT_NO_SUPPORTED_RECIPE')


def document_learning_spec(practice,heldout,transfer):
    from ..open_agency.learning import LearningCase,LearningSpec
    def case(key,context,data):return LearningCase(case_id=key,context=context,data=data,expected=expected_outline(data))
    return LearningSpec(learning_key='learn.markdown-outline',domain='markdown-outline',baseline_method='MD_OUTLINE_1',hypotheses=tuple(f'MD_OUTLINE_{n}' for n in range(2,7)),
        practice=(case('doc-practice','documentation-navigation',practice),),evaluation=(case('doc-heldout','documentation-navigation',heldout),),transfer=(case('doc-transfer','operator-guide',transfer),))
