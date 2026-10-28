"""Commit only intended-public delivery links to the repository; never credentials."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request


def publish(folder,env=None):
    env=os.environ if env is None else env
    source=folder/'publication.json'
    if not source.is_file():
        raise RuntimeError('No verified public video link is available. Configure PUBLIC_URL and R2 secrets.')
    item=json.loads(source.read_text())
    slug=item['episode_id']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError('Invalid publication id.')
    # The allowlist prevents bucket configuration or credentials from entering the index.
    fields=('episode_id','source_revision','build_id','duration_seconds','published_at',
            'video_url','audio_url','thumbnail_url','manifest_url')
    public={key:item[key] for key in fields}
    body=(json.dumps(public,indent=2)+'\n').encode()
    repo=env['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('Invalid repository.')
    url=f'https://api.github.com/repos/{repo}/contents/published/{slug}.json'
    headers={'Authorization':'Bearer '+env['GITHUB_TOKEN'],'Accept':'application/vnd.github+json',
             'Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28'}
    for attempt in range(3):
        current=None
        try:
            with urllib.request.urlopen(urllib.request.Request(url+'?ref=main',headers=headers),timeout=30) as response:
                current=json.load(response)
        except urllib.error.HTTPError as error:
            if error.code!=404:raise RuntimeError(f'Cannot read publication index (GitHub status {error.code}).') from None
        payload={'message':f'Publish video link for {slug}','branch':'main','content':base64.b64encode(body).decode()}
        if current:payload['sha']=current['sha']
        try:
            request=urllib.request.Request(url,headers=headers,method='PUT',data=json.dumps(payload).encode())
            with urllib.request.urlopen(request,timeout=30):pass
            print(f'Public delivery links saved in published/{slug}.json')
            return
        except urllib.error.HTTPError as error:
            if error.code not in (409,422) or attempt==2:
                raise RuntimeError(f'Cannot write publication index (GitHub status {error.code}). R2 files remain uploaded.') from None


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    publish(parser.parse_args().folder)
