"""Small local Ollama SDK adapter; no Nana Core or model-management state."""
from ipaddress import ip_address
from urllib.parse import urlsplit


class LocalOllama:
    """Call an explicitly selected loopback Ollama service with its official SDK.

    A loopback address is not process identity: another process can reuse a
    port. The operator is responsible for trusting the local service. No model
    is downloaded, started, retried or selected automatically.
    """
    def __init__(self, host='http://127.0.0.1:11434', *, timeout=120):
        if type(host) is not str or type(timeout) not in (int,float) or not 0<timeout<=600:
            raise ValueError('invalid local model settings')
        url=urlsplit(host)
        try:port=url.port
        except ValueError as exc:raise ValueError('invalid local endpoint') from exc
        try:loopback=url.hostname=='localhost' or ip_address(url.hostname or '').is_loopback
        except ValueError:loopback=False
        if (url.scheme!='http' or not loopback or not port or url.username or url.password or
                url.path not in ('','/') or url.query or url.fragment):
            raise ValueError('explicit loopback HTTP origin required')
        from ollama import Client
        # The upstream SDK can inherit OLLAMA_API_KEY. Local keyless requests
        # must not accidentally send that unrelated environment credential.
        def strip_authorization(request):request.headers.pop('authorization',None)
        self._client=Client(host=host,timeout=timeout,trust_env=False,follow_redirects=False,
                            event_hooks={'request':[strip_authorization]})

    def close(self):
        self._client.close()

    def __enter__(self):return self
    def __exit__(self,*_):self.close()

    def models(self):
        """Return models reported by the selected service; no capabilities inferred."""
        return [item.model for item in self._client.list().models if item.model]

    def chat(self, model, text, *, stream=False):
        """Return official SDK ChatResponse or its stream iterator; no auto retry."""
        if (type(model) is not str or not 1<=len(model)<=256 or any(ord(c)<32 for c in model) or
                type(text) is not str or not 1<=len(text)<=100000 or type(stream) is not bool):
            raise ValueError('invalid local model request')
        return self._client.chat(model=model,messages=[{'role':'user','content':text}],stream=stream)
