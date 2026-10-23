"""Bounded semantic HTML state: data proposals, never success or permission."""
from html.parser import HTMLParser
import re
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import digest

class PageLink(DTO):
    href:str=Field(max_length=256)
    label:str=Field(max_length=128)
class PageForm(DTO):
    action:str=Field(max_length=256)
    method:Literal['GET','POST']
    fields:tuple[str,...]=Field(max_length=16)
    buttons:tuple[str,...]=Field(max_length=8)
class PageState(DTO):
    path:str
    source_digest:str
    task_id:str|None=None
    revision:int|None=None
    title:str=''
    text:str
    links:tuple[PageLink,...]
    forms:tuple[PageForm,...]
    error:bool
    interpretation:Literal['MODEL_DERIVATION']='MODEL_DERIVATION'
    execution_authority:Literal[False]=False
    proves_effect:Literal[False]=False

class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.count=0;self.hidden=0;self.text=[];self.links=[];self.forms=[];self.form=None;self.link=None;self.title=[];self.in_title=False;self.task=None;self.revision=None;self.error=False
    def handle_starttag(self,tag,attrs):
        self.count+=1
        if self.count>512:raise CoreError('BROWSER_DOM_BOUND')
        a=dict(attrs)
        if tag in {'script','style','template'}:self.hidden+=1
        if self.hidden:return
        if a.get('data-task'):
            if not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',a['data-task']):raise CoreError('BROWSER_MALFORMED_PAGE')
            self.task=a['data-task']
        if a.get('data-revision','').isdigit():self.revision=int(a['data-revision'])
        if a.get('role')=='alert' or a.get('data-error')=='true':self.error=True
        if tag=='title':self.in_title=True
        if tag=='a':
            if len(a.get('href',''))>256:raise CoreError('BROWSER_MALFORMED_PAGE')
            self.link={'href':a.get('href',''),'label':''}
        if tag=='form':
            if self.form is not None:raise CoreError('BROWSER_MALFORMED_PAGE')
            method=a.get('method','GET').upper()
            if method not in {'GET','POST'}:raise CoreError('BROWSER_FORM_METHOD_DENIED')
            if len(a.get('action',''))>256:raise CoreError('BROWSER_MALFORMED_PAGE')
            self.form={'action':a.get('action',''),'method':method,'fields':[],'buttons':[]}
        if self.form is not None:
            if tag in {'input','textarea','select'} and a.get('name'):
                if len(a['name'])>32:raise CoreError('BROWSER_MALFORMED_PAGE')
                self.form['fields'].append(a['name'])
            if tag=='button':self.form['buttons'].append(a.get('name') or a.get('aria-label') or a.get('type','submit'))
    def handle_endtag(self,tag):
        if tag in {'script','style','template'}:
            self.hidden=max(0,self.hidden-1);return
        if self.hidden:return
        if tag=='title':self.in_title=False
        if tag=='a' and self.link:self.links.append(self.link);self.link=None
        if tag=='form' and self.form:self.forms.append(self.form);self.form=None
    def handle_data(self,data):
        if self.hidden:return
        t=' '.join(data.split())
        if t:self.text.append(t)
        if self.in_title:self.title.append(t)
        if self.link:self.link['label']=(self.link['label']+' '+t).strip()[:128]

def parse_page(path,raw):
    if len(raw)>32768:raise CoreError('BROWSER_PAGE_BOUND')
    try:
        parser=_Page();parser.feed(raw.decode('utf-8'));parser.close()
        if parser.form is not None or len(parser.forms)>8 or len(parser.links)>32:raise CoreError('BROWSER_MALFORMED_PAGE')
        return PageState(path=path,source_digest=digest(raw),task_id=parser.task,revision=parser.revision,title=' '.join(parser.title)[:128],text=' '.join(parser.text)[:4096],links=tuple(PageLink(**v) for v in parser.links),forms=tuple(PageForm(**{**v,'fields':tuple(v['fields']),'buttons':tuple(v['buttons'])}) for v in parser.forms),error=parser.error)
    except (UnicodeError,ValueError):raise CoreError('BROWSER_MALFORMED_PAGE') from None
