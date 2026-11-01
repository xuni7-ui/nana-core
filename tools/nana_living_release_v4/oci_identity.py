"""Derive a manifest/config binding from the sealed Docker image archive.

No daemon-selected alias is trusted without comparing it with these bytes.
Only bounded OCI image archives with a single manifest are accepted.
"""
import gzip
import hashlib
import io
import json
import re
import tarfile
import zlib
from pathlib import Path


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('OCI_DUPLICATE_KEY')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs)


class Parts(io.RawIOBase):
    def __init__(self, paths):
        self.paths, self.stream = iter(paths), None
    def readable(self): return True
    def readinto(self, buffer):
        while True:
            if self.stream is None:
                path=next(self.paths,None)
                if path is None:return 0
                self.stream=Path(path).open('rb')
            size=self.stream.readinto(buffer)
            if size:return size
            self.stream.close();self.stream=None
    def close(self):
        if self.stream:self.stream.close()
        super().close()


def inspect_archive(paths, config_pin):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',config_pin):raise ValueError('PINNED_IMAGE_REQUIRED')
    blobs={};small={};index=None
    with io.BufferedReader(Parts(paths)) as joined, gzip.GzipFile(fileobj=joined) as compressed, tarfile.open(fileobj=compressed,mode='r|') as archive:
        for member in archive:
            if not member.isfile():continue
            if member.name=='index.json':
                if index is not None or member.size>1048576:raise ValueError('OCI_INDEX_INVALID')
                index=strict_json(archive.extractfile(member).read());continue
            prefix='blobs/sha256/'
            if not member.name.startswith(prefix):continue
            key=member.name[len(prefix):]
            if not re.fullmatch(r'[a-f0-9]{64}',key) or key in blobs or member.size>4*1024**3:raise ValueError('OCI_BLOB_INVALID')
            f=archive.extractfile(member);h=hashlib.sha256();smallbuf=bytearray();size=0;expanded=0;uncompressed=hashlib.sha256();dec=None
            while chunk:=f.read(1048576):
                if size==0 and chunk.startswith(b'\x1f\x8b'):dec=zlib.decompressobj(16+zlib.MAX_WBITS)
                size+=len(chunk);h.update(chunk)
                if member.size<=1048576:smallbuf.extend(chunk)
                if dec:
                    remaining=chunk
                    while remaining:
                        data=dec.decompress(remaining,1048576);remaining=dec.unconsumed_tail
                        expanded+=len(data);uncompressed.update(data)
                        if expanded>4*1024**3:raise ValueError('OCI_LAYER_SIZE_BOUND')
                    if dec.unused_data:raise ValueError('OCI_LAYER_TRAILING_DATA')
                else:
                    expanded+=len(chunk);uncompressed.update(chunk)
            if size!=member.size or h.hexdigest()!=key or dec and not dec.eof:raise ValueError('OCI_BLOB_DIGEST_MISMATCH')
            blobs['sha256:'+key]=(size,'sha256:'+uncompressed.hexdigest())
            if smallbuf:small['sha256:'+key]=bytes(smallbuf)
    refs=index.get('manifests') if isinstance(index,dict) else None
    if not isinstance(refs,list) or len(refs)!=1:raise ValueError('OCI_INDEX_INVALID')
    ref=refs[0];mid=ref.get('digest');
    if mid==config_pin or mid not in small or blobs[mid][0]!=ref.get('size'):raise ValueError('OCI_MANIFEST_INVALID')
    manifest=strict_json(small[mid]);c=manifest.get('config',{});cid=c.get('digest')
    if cid!=config_pin or cid not in small or blobs[cid][0]!=c.get('size'):raise ValueError('OCI_CONFIG_MISMATCH')
    config=strict_json(small[cid]);layers=manifest.get('layers');diff=config.get('rootfs',{}).get('diff_ids')
    if not isinstance(layers,list) or not isinstance(diff,list) or not layers or len(layers)!=len(diff):raise ValueError('OCI_LAYER_MISMATCH')
    for layer,expected in zip(layers,diff):
        digest=layer.get('digest');value=blobs.get(digest)
        if value is None or value!=(layer.get('size'),expected):raise ValueError('OCI_LAYER_MISMATCH')
    if config.get('os')!='linux' or config.get('architecture')!='amd64' or config.get('config',{}).get('User')!='999:999':raise ValueError('IMAGE_RUNTIME_CONTRACT_MISMATCH')
    return {'manifest_id':mid,'config_id':cid,'diff_ids':diff,'manifest_size':ref['size'],'config_size':c['size']}
