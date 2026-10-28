import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from discover_episodes import select
from episode_package import asset_path
from render_episode import validate
from upload_r2 import upload


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        p=self.root/'input/test-episode'
        p.mkdir(parents=True)
        (self.root/'shared.png').write_bytes(b'image')
        self.path=p/'episode.json'
        self.data={'id':'test-episode','ready':True,'assets':{'background':'../../shared.png'}}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data))

    def test_script_and_shared_image_changes_select_episode(self):
        for change in ['input/test-episode/episode.json','input/test-episode/prompts.md','shared.png']:
            self.assertEqual(select(self.root,[change])[0]['slug'],'test-episode')
        self.assertEqual(select(self.root,['README.md']),[])

    def test_draft_can_be_committed_before_image(self):
        self.data['ready']=False
        self.data['assets']['background']='missing.png'
        self.save()
        self.assertEqual(select(self.root),[])
        self.data['ready']=True
        self.save()
        with self.assertRaisesRegex(ValueError,'Missing episode asset'):
            select(self.root)

    def test_script_change_rebuilds_ready_packages(self):
        self.assertEqual(len(select(self.root,['scripts/render_episode.py'])),1)

    def test_asset_escape_and_invalid_requested_id(self):
        with self.assertRaises(ValueError):asset_path(self.path.parent,'../../../outside.png',self.root)
        with self.assertRaises(ValueError):select(self.root,episode='../invalid')

    def test_a2_named_characters_and_positions(self):
        data=json.loads((ROOT/'episodes/cafe_a1.json').read_text())
        data['level']='A2'
        data['speakers']={'son':{**data['speakers']['male'],'position':'left'},
                          'mother':{**data['speakers']['female'],'position':'right'}}
        for line in data['lines']:
            line['speaker']='son' if line['speaker']=='male' else 'mother'
        validate(data)
        data['speakers']['mother']['position']='left'
        with self.assertRaises(ValueError):validate(data)


class FakeStorage:
    def __init__(self,fail=False):self.keys=[];self.objects={};self.fail=fail
    def upload_file(self,filename,bucket,key,ExtraArgs):
        if self.fail:raise RuntimeError('Upload failed')
        self.keys.append(key)
        self.objects[key]=Path(filename).read_bytes()
    def head_object(self,Bucket,Key):return {'ContentLength':len(self.objects[Key])}


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        content=b'verified test media'
        (self.folder/'podcast.mp4').write_bytes(content)
        self.manifest={'id':'test-episode','revision':'a'*40,'build_id':'123-1','sample':False,'files':[
            {'name':'podcast.mp4','size':len(content),'sha256':hashlib.sha256(content).hexdigest(),'content_type':'video/mp4'}]}
        self.save()
        self.env={key:'test-value' for key in ('R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME')}
        self.env['R2_ACCOUNT_ID']='b'*32

    def save(self):(self.folder/'manifest.json').write_text(json.dumps(self.manifest))

    def test_no_credentials_keeps_artifacts_and_partial_config_fails(self):
        storage=FakeStorage()
        self.assertIsNone(upload(self.folder,{},storage));self.assertEqual(storage.keys,[])
        with self.assertRaises(ValueError):upload(self.folder,{'R2_ACCOUNT_ID':'test'},storage)

    def test_versioned_upload_and_manifest_last(self):
        storage=FakeStorage();report=upload(self.folder,self.env,storage)
        self.assertEqual(storage.keys,[f'episodes/test-episode/{"a"*40}/123-1/podcast.mp4',report['manifest_key']])
        self.assertTrue((self.folder/'r2-upload.json').exists())

    def test_tampering_rejected_before_network(self):
        (self.folder/'podcast.mp4').write_bytes(b'modified')
        storage=FakeStorage()
        with self.assertRaises(ValueError):upload(self.folder,self.env,storage)
        self.assertEqual(storage.keys,[])

    def test_sample_is_never_published(self):
        self.manifest['sample']=True;self.save();storage=FakeStorage()
        self.assertIsNone(upload(self.folder,self.env,storage));self.assertEqual(storage.keys,[])

    def test_failed_upload_does_not_write_completion_manifest(self):
        storage=FakeStorage(fail=True)
        with self.assertRaises(RuntimeError):upload(self.folder,self.env,storage)
        self.assertEqual(storage.keys,[])
        self.assertFalse((self.folder/'r2-upload.json').exists())


if __name__=='__main__':unittest.main()
