"""Inspect an already-uploaded delivery without re-rendering; publish public-only diagnostics."""
import base64
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from upload_r2 import settings
import boto3
from botocore.config import Config

job=json.loads(Path('.github/r2-recovery.json').read_text())
prefix=job['prefix']
if not re.fullmatch(r'episodes/[a-z0-9-]+/[a-f0-9]{40}/[0-9]+-[0-9]+',prefix):raise ValueError('Invalid delivery prefix')
config=settings(os.environ)
client=boto3.client('s3',endpoint_url=config['endpoint_url'],region_name='auto',
                    aws_access_key_id=config['R2_ACCESS_KEY_ID'],aws_secret_access_key=config['R2_SECRET_ACCESS_KEY'],
                    config=Config(request_checksum_calculation='when_required',response_checksum_validation='when_required'))
manifest=json.loads(client.get_object(Bucket=config['R2_BUCKET_NAME'],Key=prefix+'/manifest.json')['Body'].read())
expected=next(x['size'] for x in manifest['files'] if x['name']=='podcast.mp4')
assert client.head_object(Bucket=config['R2_BUCKET_NAME'],Key=prefix+'/podcast.mp4')['ContentLength']==expected
base=config['public_url']
url=base+'/'+prefix+'/podcast.mp4'
checks=[]
for method in ['HEAD','GET']:
    headers={'User-Agent':'Mozilla/5.0 (compatible; GermanLessonDelivery/1.0)'}
    if method=='GET':headers['Range']='bytes=0-0'
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers),timeout=30) as response:
            check={'method':method,'status':response.status,'length':response.headers.get('Content-Length'),
                   'range':response.headers.get('Content-Range'),'type':response.headers.get('Content-Type')}
            total=(check['range'] or '').rsplit('/',1)[-1] if check['range'] else check['length']
            check['verified']=response.status in (200,206) and str(total)==str(expected)
            if method=='GET':response.read(1)
    except urllib.error.HTTPError as error:check={'method':method,'status':error.code,'verified':False}
    except Exception as error:check={'method':method,'error':type(error).__name__,'verified':False}
    checks.append(check)
item={'episode_id':manifest['id'],'source_revision':manifest['revision'],'build_id':manifest['build_id'],
      'duration_seconds':manifest['duration_seconds'],'published_at':'recovered-existing-delivery',
      'video_url':url,'audio_url':base+'/'+prefix+'/podcast.mp3',
      'thumbnail_url':base+'/'+prefix+'/thumbnail.png','manifest_url':base+'/'+prefix+'/manifest.json',
      'public_verified':any(c['verified'] for c in checks),'public_checks':checks}
# PUBLIC_URL is the user's intended-public viewer domain. No authentication fields are exported.
repo=os.environ['GITHUB_REPOSITORY'];slug=manifest['id']
api=f'https://api.github.com/repos/{repo}/contents/published/{slug}.json'
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json',
         'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'}
current=None
try:
    with urllib.request.urlopen(urllib.request.Request(api+'?ref=main',headers=headers),timeout=30) as response:current=json.load(response)
except urllib.error.HTTPError as error:
    if error.code!=404:raise
payload={'message':'Record public delivery check for '+slug,'branch':'main',
         'content':base64.b64encode((json.dumps(item,indent=2)+'\n').encode()).decode()}
if current:payload['sha']=current['sha']
with urllib.request.urlopen(urllib.request.Request(api,method='PUT',headers=headers,data=json.dumps(payload).encode()),timeout=30):pass
print('Public checks:',json.dumps(checks))
print('Public-only delivery status saved to published/'+slug+'.json')
