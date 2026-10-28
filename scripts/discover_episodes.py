"""Select ready episode folders affected by a commit, including shared image edits."""
import argparse
import json
from pathlib import Path
import subprocess
from episode_package import ROOT, load_package, SLUG, read_source


def select(root, changed=None, episode=None):
    if episode and not SLUG.fullmatch(episode):
        raise ValueError('Invalid episode id.')
    shared = changed is None or any(p.startswith(('scripts/', 'tests/')) or p in (
        'requirements.txt', '.github/workflows/podcast.yml') for p in changed)
    selected = []
    paths=sorted((root/'input').glob('*.md'))+sorted((root/'input').glob('*/episode.json'))
    seen=set()
    for path in paths:
        if path.stem.startswith('_') or path.parent.name.startswith('_'):
            continue
        raw=read_source(path)
        if raw.get('ready') is not True:
            continue
        slug=raw.get('id','')
        if slug in seen:raise ValueError(f'Duplicate episode id: {slug}')
        seen.add(slug)
        if episode and slug!=episode:continue
        source=path.relative_to(root).as_posix()
        affected=shared or episode or source in changed or (path.suffix=='.json' and any(p.startswith(f'input/{path.parent.name}/') for p in changed))
        if not affected:
            assets=raw.get('assets',{})
            affected=any((path.parent/value).resolve().relative_to(root.resolve()).as_posix() in changed for value in assets.values() if value)
        if affected:
            data,_=load_package(path,root)
            selected.append({'slug':data['id'],'episode':source})
    if episode and not selected:
        raise ValueError(f'No ready episode found: {episode}')
    return selected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--episode')
    args = parser.parse_args()
    changed = None
    if args.base and set(args.base) != {'0'}:
        output = subprocess.check_output(['git','diff','--name-only',args.base,args.head],cwd=ROOT,text=True)
        changed = output.splitlines()
    print(json.dumps({'include':select(ROOT,changed,args.episode)}))
