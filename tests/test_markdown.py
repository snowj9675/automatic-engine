import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from discover_episodes import select
from markdown_episode import read_markdown
from episode_package import load_package
from upload_r2 import settings, upload, check_public_video
from test_production import FakeStorage


class MarkdownTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'input').mkdir();(self.root/'images').mkdir()
        (self.root/'images/cafe.png').write_bytes(b'image')
        self.path=self.root/'input/cafe-test.md'
        self.text='''---
id: cafe-test
title: Im Café
level: A1
image_ready: true
image: ../images/cafe.png
---
# Lesson
## Image prompt
Exactly two people.
## Dialogue
| Speaker | German | English |
|---|---|---|
| Ben | Hallo, Anna! | Hello, Anna! |
| Anna | Einen Tee, bitte. | A tea, please. |
## Thumbnail prompt
Use the same characters.
'''
        self.path.write_text(self.text)

    def test_single_file_compiles_and_is_discovered(self):
        data,image=load_package(self.path,self.root)
        self.assertEqual(len(data['lines']),2)
        self.assertEqual(data['speakers']['female']['voice'],'de-DE-SeraphinaMultilingualNeural')
        self.assertEqual(data['speakers']['male']['voice'],'de-DE-FlorianMultilingualNeural')
        self.assertTrue(all(s['engine']=='edge' for s in data['speakers'].values()))
        self.assertEqual(data['rate'],'+0%')
        self.assertEqual(image,self.root/'images/cafe.png')
        self.assertEqual(select(self.root,['input/cafe-test.md'])[0]['episode'],'input/cafe-test.md')
        self.assertEqual(len(select(self.root,['images/cafe.png'])),1)

    def test_image_false_waits_without_requiring_file(self):
        self.path.write_text(self.text.replace('image_ready: true','image_ready: false'))
        (self.root/'images/cafe.png').unlink()
        self.assertEqual(select(self.root),[])

    def test_true_requires_existing_image(self):
        (self.root/'images/cafe.png').unlink()
        with self.assertRaisesRegex(ValueError,'Missing episode asset'):select(self.root)

    def test_flag_must_be_boolean_and_speaker_must_exist(self):
        self.path.write_text(self.text.replace('image_ready: true','image_ready: "false"'))
        with self.assertRaises(ValueError):read_markdown(self.path)
        self.path.write_text(self.text.replace('| Ben |','| Unknown |'))
        with self.assertRaises(ValueError):read_markdown(self.path)


class NewSecretsTests(unittest.TestCase):
    def setUp(self):
        self.env={'ACCESS_KEY_ID':'test-key','SECRET_ACCESS_KEY':'test-secret','BUCKET_NAME':'test-bucket',
                  'S3_API':'https://'+'a'*32+'.r2.cloudflarestorage.com/test-bucket',
                  'PUBLIC_URL':'https://public.example.com/'}

    def test_bucket_s3_url_is_normalized(self):
        config=settings(self.env)
        self.assertEqual(config['endpoint_url'],'https://'+'a'*32+'.r2.cloudflarestorage.com')
        self.assertEqual(config['public_url'],'https://public.example.com')

    def test_partial_or_non_r2_config_fails(self):
        with self.assertRaises(ValueError):settings({'ACCESS_KEY_ID':'test'})
        self.env['S3_API']='https://not-r2.example.com'
        with self.assertRaises(ValueError):settings(self.env)

    def test_verified_publication_contains_no_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);content=b'video'
            (folder/'podcast.mp4').write_bytes(content)
            import hashlib
            manifest={'id':'test','revision':'a'*40,'build_id':'123-1','sample':False,'duration_seconds':1,
                      'files':[{'name':'podcast.mp4','size':len(content),'sha256':hashlib.sha256(content).hexdigest(),'content_type':'video/mp4'}]}
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with patch('upload_r2.check_public_video') as check:
                upload(folder,self.env,FakeStorage())
                self.assertEqual(check.call_count,1)
            public=(folder/'publication.json').read_text()
            self.assertNotIn('test-secret',public);self.assertNotIn('test-key',public)
            self.assertIn('https://public.example.com/episodes/test/',public)



class PublicAccessTests(unittest.TestCase):
    def test_browser_agent_and_range_fallback(self):
        from unittest.mock import MagicMock
        from urllib.error import HTTPError
        response=MagicMock()
        response.__enter__.return_value=response
        response.status=206
        response.headers={'Content-Length':'1','Content-Range':'bytes 0-0/1234'}
        with patch('upload_r2.urlopen',side_effect=[HTTPError('https://example.com/video',405,'HEAD unsupported',{},None),response]) as open_url:
            check_public_video('https://example.com/video',1234)
            requests=[call.args[0] for call in open_url.call_args_list]
            self.assertIn('Mozilla/5.0',requests[0].get_header('User-agent'))
            self.assertEqual(requests[1].get_header('Range'),'bytes=0-0')

if __name__=='__main__':unittest.main()
