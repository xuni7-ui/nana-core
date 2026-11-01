import gzip,hashlib,io,json,tarfile
import pytest
from tools.nana_living_release_v4.oci_identity import inspect_archive
from tools.nana_living_release_v4.deploy import DockerError, image_identity, resolve


def compact(value):return json.dumps(value,separators=(',',':')).encode()
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()


def artifact(root):
    layer=b'TEST_ONLY_NOT_SECRET_OCI_LAYER';ld=digest(layer)
    config=compact({'os':'linux','architecture':'amd64','config':{'User':'999:999'},'rootfs':{'diff_ids':[ld]}});cid=digest(config)
    manifest=compact({'schemaVersion':2,'config':{'digest':cid,'size':len(config)},'layers':[{'digest':ld,'size':len(layer)}]});mid=digest(manifest)
    index=compact({'schemaVersion':2,'manifests':[{'digest':mid,'size':len(manifest)}]})
    part=root/'image.gz'
    with gzip.open(part,'wb') as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
        for name,raw in [('index.json',index),*[(f'blobs/sha256/{digest(value)[7:]}',value) for value in (layer,config,manifest)]]:
            info=tarfile.TarInfo(name);info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
    image={'id':cid,'manifest_id':mid,'manifest_size':len(manifest),'config_size':len(config),'parts':['image.gz'],'gzip_sha256':hashlib.sha256(part.read_bytes()).hexdigest()}
    return image,[ld]


class Daemon:
    def __init__(self,pin,alias,layers,*,actual=None,user='999:999'):
        self.pin,self.alias,self.layers,self.actual,self.user=pin,alias,layers,actual or alias,user
    def image(self,key):
        if key==self.pin:raise DockerError('DOCKER_HTTP_404')
        if key!=self.alias:raise DockerError('DOCKER_HTTP_404')
        return {'id':self.actual,'diff_ids':self.layers,'architecture':'amd64','os':'linux','user':self.user}


def test_containerd_manifest_alias_is_bound_to_actual_config_and_layers(tmp_path):
    image,layers=artifact(tmp_path);proof=image_identity(tmp_path,image)
    assert proof['config_id']==image['id'] and proof['manifest_id']==image['manifest_id']
    assert resolve(Daemon(image['id'],image['manifest_id'],layers),image,proof)==image['manifest_id']


def test_alias_confusion_self_reference_sizes_and_config_are_denied(tmp_path):
    image,layers=artifact(tmp_path);proof=image_identity(tmp_path,image)
    for broken in ({**image,'manifest_id':image['id']},{**image,'manifest_id':'sha256:'+'f'*64},
                   {**image,'manifest_size':image['manifest_size']+1},{**image,'config_size':image['config_size']+1},
                   {**image,'id':'sha256:'+'e'*64}):
        with pytest.raises(ValueError):image_identity(tmp_path,broken)
    with pytest.raises(ValueError,match='IMAGE_IDENTITY_MISMATCH'):
        resolve(Daemon(image['id'],image['manifest_id'],layers,actual='sha256:'+'d'*64),image,proof)
    with pytest.raises(ValueError,match='IMAGE_LAYER_MISMATCH'):
        resolve(Daemon(image['id'],image['manifest_id'],['sha256:'+'a'*64]),image,proof)
    with pytest.raises(ValueError,match='IMAGE_RUNTIME_CONTRACT_MISMATCH'):
        resolve(Daemon(image['id'],image['manifest_id'],layers,user='0:0'),image,proof)


def test_archive_corruption_is_not_masked_by_resigning_manifest(tmp_path):
    image,_=artifact(tmp_path);p=tmp_path/'image.gz';data=p.read_bytes();p.write_bytes(data[:-5]+b'xxxxx')
    with pytest.raises(ValueError,match='IMAGE_PARTS_COMBINED_MISMATCH'):image_identity(tmp_path,image)
