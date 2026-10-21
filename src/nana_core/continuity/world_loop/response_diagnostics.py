"""Allowlisted parser structure only: no input values, prose, headers or secrets."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO

Stage=Literal['HTTP','OUTER_JSON','ENVELOPE','CHOICES','MESSAGE','FINISH','CONTENT','SEMANTIC_JSON','SEMANTIC_SCHEMA','USAGE','MODEL','COMPLETE']
TypeName=Literal['MISSING','NULL','BOOLEAN','INTEGER','NUMBER','STRING','ARRAY','OBJECT','UNKNOWN']

class ParseIssue(DTO):
    path:str=Field(max_length=192,pattern=r'^[$A-Za-z0-9_.\[\]-]+$')
    expected:Literal['JSON','OBJECT','ARRAY','NONEMPTY_ARRAY','ASSISTANT','TEXT','STOP','MODEL_ID','SCHEMA','PRESENT','NO_EXTRA_FIELDS','STRING','NUMBER','INTEGER','NONNEGATIVE_INTEGER','ALLOWED_ENUM','CONSTRAINT','NO_TOOL_CALLS']
    actual_type:TypeName

class ResponseDiagnostic(DTO):
    version:Literal[1]=1
    stage:Stage
    json_valid:bool|None=None
    openai_shape_valid:bool|None=None
    semantic_json_valid:bool|None=None
    strict_schema_valid:bool|None=None
    model_matches_request:bool|None=None
    issues:tuple[ParseIssue,...]=Field(default=(),max_length=4)


def type_name(value,missing=False):
    if missing:return 'MISSING'
    return {type(None):'NULL',bool:'BOOLEAN',int:'INTEGER',float:'NUMBER',str:'STRING',list:'ARRAY',dict:'OBJECT'}.get(type(value),'UNKNOWN')


def schema_issues(error,payload,schema):
    # Pydantic messages, inputs, ctx and URLs can echo private/credential values.
    # Only schema-known location components and coarse types may leave memory.
    allowed=set()
    def keys(node):
        if isinstance(node,dict):
            allowed.update(node.get('properties',{}))
            for child in node.values():keys(child)
        elif isinstance(node,list):
            for child in node:keys(child)
    keys(schema)
    expected={'missing':'PRESENT','extra_forbidden':'NO_EXTRA_FIELDS','string_type':'STRING','float_type':'NUMBER','float_parsing':'NUMBER','int_type':'INTEGER','int_parsing':'INTEGER','literal_error':'ALLOWED_ENUM','model_type':'OBJECT','tuple_type':'ARRAY','list_type':'ARRAY'}
    out=[]
    for item in error.errors(include_input=False,include_context=False,include_url=False)[:4]:
        path='$.choices[0].message.content.$semantic';value=payload;missing=False
        for key in item['loc'][:12]:
            if type(key) is int and 0<=key<=63:
                path+='['+str(key)+']';value=value[key] if isinstance(value,list) and key<len(value) else None
            elif type(key) is str and key in allowed:
                path+='.'+key
                if isinstance(value,dict):missing=key not in value;value=value.get(key)
                else:value=None
            else:
                path+='.$unknown'
                if type(key) is str and isinstance(value,dict):missing=key not in value;value=value.get(key)
                else:value=None
        out.append(ParseIssue(path=path[:192],expected=expected.get(item['type'],'CONSTRAINT'),actual_type=type_name(value,missing)))
    return tuple(out)
