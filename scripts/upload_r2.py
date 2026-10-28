"""Publish verified deliverables to a versioned R2 prefix; manifest is uploaded last."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

KEYS=('R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME')


def settings(env):
    configured=[bool(env.get(key)) for key in KEYS]
    if not any(configured):
        return None
    if not all(configured):
        raise ValueError('R2 is partially configured. Set all four R2 secrets or remove them to use GitHub artifacts only.')
    if not re.fullmatch(r'[a-fA-F0-9]{32}',env['R2_ACCOUNT_ID']):
        raise ValueError('R2_ACCOUNT_ID must be the 32-character Cloudflare account id.')
    return {key:env[key] for key in KEYS}


def upload(folder,env=None,client=None):
    env=os.environ if env is None else env
    config=settings(env)
    if config is None:
        print('R2 is not configured; deliverables remain available as GitHub artifacts.')
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
        client=boto3.client('s3',endpoint_url=f"https://{config['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
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
    public=env.get('R2_PUBLIC_BASE_URL','').rstrip('/')
    if public:
        report['video_url']=f'{public}/{prefix}/podcast.mp4'
    (folder/'r2-upload.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Uploaded complete episode to R2: {prefix}')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    upload(parser.parse_args().folder)
