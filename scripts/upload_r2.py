"""Publish verified deliverables to a versioned R2 prefix; manifest is uploaded last."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

KEYS=('R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME')


def settings(env):
    new_keys=('ACCESS_KEY_ID','SECRET_ACCESS_KEY','BUCKET_NAME','S3_API','PUBLIC_URL')
    if any(env.get(key) for key in new_keys):
        missing=[key for key in new_keys if not env.get(key)]
        if missing:raise ValueError('Missing R2 settings: '+', '.join(missing))
        endpoint=env['S3_API'].strip().rstrip('/')
        if '://' not in endpoint:endpoint='https://'+endpoint
        parts=urlsplit(endpoint)
        if parts.scheme!='https' or parts.username or parts.password or parts.port or parts.query or parts.fragment or not re.fullmatch(r'[a-fA-F0-9]{32}(?:\.[a-z0-9-]+)?\.r2\.cloudflarestorage\.com',parts.hostname or ''):
            raise ValueError('S3_API must be your HTTPS Cloudflare R2 S3 endpoint.')
        if parts.path.strip('/') not in ('',env['BUCKET_NAME']):
            raise ValueError('S3_API may end in the configured bucket name, but no other path.')
        public=env['PUBLIC_URL'].strip().rstrip('/')
        pp=urlsplit(public)
        if pp.scheme!='https' or not pp.hostname or pp.username or pp.password or pp.query or pp.fragment:
            raise ValueError('PUBLIC_URL must be the HTTPS public bucket/domain base URL.')
        return {'R2_ACCESS_KEY_ID':env['ACCESS_KEY_ID'],'R2_SECRET_ACCESS_KEY':env['SECRET_ACCESS_KEY'],
                'R2_BUCKET_NAME':env['BUCKET_NAME'],'endpoint_url':f'https://{parts.netloc}', 'public_url':public}
    configured=[bool(env.get(key)) for key in KEYS]
    if not any(configured):return None
    if not all(configured):raise ValueError('R2 is partially configured. Set all required R2 secrets.')
    if not re.fullmatch(r'[a-fA-F0-9]{32}',env['R2_ACCOUNT_ID']):raise ValueError('R2_ACCOUNT_ID must be a Cloudflare account id.')
    return {**{key:env[key] for key in KEYS},'endpoint_url':f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            'public_url':env.get('R2_PUBLIC_BASE_URL','').rstrip('/')}


def check_public_video(url, expected_size):
    headers={'User-Agent':'Mozilla/5.0 (compatible; GermanLessonDelivery/1.0)'}
    for attempt in range(3):
        for method in ('HEAD','GET'):
            request_headers=dict(headers)
            if method=='GET':request_headers['Range']='bytes=0-0'
            try:
                with urlopen(Request(url,method=method,headers=request_headers),timeout=20) as response:
                    content_range=response.headers.get('Content-Range')
                    size=content_range.rsplit('/',1)[-1] if content_range else response.headers.get('Content-Length','0')
                    if int(size)!=expected_size or response.status not in (200,206):
                        raise ValueError('Public video size or status differs from the uploaded file.')
                    if method=='GET':response.read(1)
                return
            except Exception:
                pass
        if attempt<2:time.sleep(attempt+1)
    raise RuntimeError('R2 transfer succeeded but public video access failed. Check PUBLIC_URL and bucket public access.')


def upload(folder,env=None,client=None):
    env=os.environ if env is None else env
    config=settings(env)
    if config is None:
        print('R2 is not configured; generated files remain on the runner. Artifact upload is disabled.')
        return None
    manifest=json.loads((folder/'manifest.json').read_text())
    slug,revision=manifest['id'],manifest['revision']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug) or not re.fullmatch(r'[a-f0-9]{7,64}',revision):
        raise ValueError('R2 publication requires a valid episode id and Git commit SHA.')
    if manifest.get('sample'):
        print('Skipping R2 upload for a short preview; only complete episodes are published.')
        return None
    build_id=manifest.get('build_id','')
    if not re.fullmatch(r'(?:[0-9]+-[0-9]+|[a-f0-9]{16})',build_id):
        raise ValueError('R2 publication requires a valid build id.')
    entries=list(manifest['files'])
    for item in entries:
        path=folder/item['name']
        if Path(item['name']).name!=item['name'] or not path.is_file():
            raise ValueError('Invalid deliverable in manifest.')
        if path.stat().st_size!=item['size'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Deliverable changed after verification.')
    if client is None:
        import boto3
        from botocore.config import Config
        client=boto3.client('s3',endpoint_url=config['endpoint_url'],
                            aws_access_key_id=config['R2_ACCESS_KEY_ID'],aws_secret_access_key=config['R2_SECRET_ACCESS_KEY'],
                            region_name='auto',config=Config(request_checksum_calculation='when_required',response_checksum_validation='when_required'))
    bucket=config['R2_BUCKET_NAME']
    prefix=f'episodes/{slug}/{revision}/{build_id}'
    # Completion marker goes last; partial failures never announce a completed episode.
    entries.append({'name':'manifest.json','content_type':'application/json'})
    for item in entries:
        path=folder/item['name']
        key=f"{prefix}/{item['name']}"
        client.upload_file(str(path),bucket,key,ExtraArgs={'ContentType':item['content_type'],
                           'Metadata':{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}})
        remote=client.head_object(Bucket=bucket,Key=key)
        if remote['ContentLength']!=path.stat().st_size:
            raise RuntimeError('R2 object size differs from local deliverable.')
    report={'bucket':bucket,'prefix':prefix,'manifest_key':f'{prefix}/manifest.json'}
    public=config.get('public_url','')
    if public:
        report['video_url']=f'{public}/{prefix}/podcast.mp4'
        check_public_video(report['video_url'],(folder/'podcast.mp4').stat().st_size)
        publication={'episode_id':slug,'source_revision':revision,'build_id':build_id,
                     'duration_seconds':manifest['duration_seconds'],'public_verified':True,
                     'published_at':datetime.now(timezone.utc).isoformat(),
                     'video_url':report['video_url'],'audio_url':f'{public}/{prefix}/podcast.mp3',
                     'thumbnail_url':f'{public}/{prefix}/thumbnail.png','manifest_url':f'{public}/{prefix}/manifest.json'}
        (folder/'publication.json').write_text(json.dumps(publication,indent=2)+'\n')
    (folder/'r2-upload.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Uploaded and verified complete episode in R2: {prefix}')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    upload(parser.parse_args().folder)
