"""Select ready episode folders affected by a commit, including shared image edits."""
import argparse
import json
from pathlib import Path
import subprocess
from episode_package import ROOT, load_package, SLUG


def select(root, changed=None, episode=None):
    if episode and not SLUG.fullmatch(episode):
        raise ValueError('Invalid episode id.')
    shared = changed is None or any(p.startswith(('scripts/', 'tests/')) or p in (
        'requirements.txt', '.github/workflows/podcast.yml') for p in changed)
    selected = []
    for path in sorted((root/'input').glob('*/episode.json')):
        if path.parent.name.startswith('_'):
            continue
        raw = json.loads(path.read_text(encoding='utf-8'))
        if raw.get('ready') is not True:
            continue
        if episode and path.parent.name != episode:
            continue
        affected = shared or episode or any(p.startswith(f'input/{path.parent.name}/') for p in changed)
        if not affected:
            # A reusable image elsewhere in the repository can affect a package.
            assets = raw.get('assets', {})
            affected = any((path.parent/value).resolve().relative_to(root.resolve()).as_posix() in changed
                           for value in assets.values() if value)
        if affected:
            data,_ = load_package(path, root)
            selected.append({'slug': data['id'], 'episode': path.relative_to(root).as_posix()})
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
