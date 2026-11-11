"""Native Messages codec on the existing bounded HTTP/session infrastructure.

Wire shape/auth/version/finish/usage are Anthropic-specific. Only the internal
proposal validator is shared; no OpenAI protocol is sent to this endpoint.
Text cognition only. No native SSE/tools/media/automatic continuation or retry.
"""
from ...storage import canonical
from .cognition import OpenAIJSONTransport, TransportFailure, strict_json
from .response_diagnostics import ParseIssue, type_name

API_VERSION = '2026-10-21'


class AnthropicJSONTransport(OpenAIJSONTransport):
    supports_json_stream = False

    def request_headers(self, request_id):
        headers={'Content-Type':'application/json','Accept':'application/json',
                 'X-Request-ID':request_id,'anthropic-version':API_VERSION}
        if self._credential:headers['x-api-key']=self._credential
        return headers

    def request_body(self, request):
        if request.response_mode != 'JSON':raise TransportFailure('PROVIDER_PARTIAL_OR_UNSUPPORTED_STREAM')
        messages=self.messages(request)
        body={'model':self.model_id,'max_tokens':request.budget.output_tokens,'stream':False,
              'system':'\n'.join(m['content'] for m in messages if m['role']=='system'),
              'messages':[m for m in messages if m['role']!='system']}
        if self.thinking_mode=='DISABLED':body['thinking']={'type':'disabled'}
        data=canonical(body).encode()
        if len(data)>196608:raise TransportFailure('PROVIDER_CONTEXT_OVERFLOW')
        return data

    def _parse_response(self, raw, request, observe):
        def require(ok,path,expected,value=None,code='PROVIDER_MALFORMED'):
            if not ok:
                self.last_parse_diagnostic=self.last_parse_diagnostic.model_copy(update={
                    'issues':(ParseIssue(path=path,expected=expected,actual_type=type_name(value)),)})
                raise TransportFailure(code)
        self.last_parse_diagnostic=self.last_parse_diagnostic.model_copy(update={'stage':'OUTER_JSON'})
        value=strict_json(raw)
        self.last_parse_diagnostic=self.last_parse_diagnostic.model_copy(update={'stage':'ENVELOPE','json_valid':True})
        require(type(value) is dict,'$','OBJECT',value)
        require(value.get('type')=='message' and value.get('role')=='assistant','$.role','ASSISTANT',value.get('role'))
        usage=value.get('usage')
        require(type(usage) is dict,'$.usage','OBJECT',usage)
        counts={}
        for key in ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens'):
            count=usage.get(key,0) if key.startswith('cache_') else usage.get(key)
            require(type(count) is int and 0<=count<=2**53-1,'$.usage.'+key,'NONNEGATIVE_INTEGER',count)
            counts[key]=count
        # Anthropic input_tokens excludes cache read/write tokens. Keep reported
        # components and account for the whole input, never invent cache savings.
        total_input=counts['input_tokens']+counts['cache_creation_input_tokens']+counts['cache_read_input_tokens']
        require(total_input<=2**53-1,'$.usage','CONSTRAINT',usage)
        normalized_usage={**counts,'uncached_input_tokens':counts['input_tokens'],'input_tokens':total_input}
        stop=value.get('stop_reason')
        require(stop!='refusal','$.stop_reason','STOP',stop,code='PROVIDER_REFUSAL')
        require(stop=='end_turn','$.stop_reason','STOP',stop,code='PROVIDER_PARTIAL_OUTPUT')
        content=value.get('content')
        require(type(content) is list and 1<=len(content)<=16,'$.content','NONEMPTY_ARRAY',content)
        texts=[]
        for part in content:
            require(type(part) is dict,'$.content','OBJECT',part)
            if part.get('type') in {'thinking','redacted_thinking'}:continue  # no private model reasoning retention
            require(part.get('type')=='text' and type(part.get('text')) is str,'$.content','TEXT',part,code='PROVIDER_PARTIAL_OUTPUT')
            texts.append(part['text'])
        # Reuse only the strict local proposal parser via an internal envelope.
        # Audit metadata keeps the native stop reason and usage, not this shape.
        normalized={'id':value.get('id'),'model':value.get('model'),'usage':normalized_usage,
                    'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':''.join(texts)}}]}
        try:
            proposal,model,_=super()._parse_response(canonical(normalized).encode(),request,observe)
        finally:
            diagnostic=self.last_parse_diagnostic
            self.last_parse_diagnostic=diagnostic.model_copy(update={'openai_shape_valid':None,
                'issues':tuple(i.model_copy(update={'path':i.path.replace('$.choices[0].message.content','$.content')}) for i in diagnostic.issues)})
        self.last_response_metadata={'finish_reason':stop,'model_returned':self._measurement_id(model),'usage':normalized_usage}
        return proposal,model,normalized_usage
