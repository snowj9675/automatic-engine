"""Load declarative episode packages. Input files are data, never executable hooks."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


def asset_path(package, value, root=ROOT):
    if not isinstance(value, str) or not value:
        raise ValueError('Asset paths must be nonempty strings.')
    candidate = (package / value).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError('Assets must remain inside the repository.')
    if not candidate.is_file():
        raise ValueError(f'Missing episode asset: {candidate.relative_to(root.resolve())}')
    return candidate


def load_package(path, root=ROOT, require_ready=True):
    path = Path(path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Episode must be inside the repository.')
    data = json.loads(path.read_text(encoding='utf-8'))
    slug = data.get('id', '')
    if not SLUG.fullmatch(slug) or slug != path.parent.name:
        raise ValueError('Episode id must match its folder: lowercase words joined by hyphens.')
    if require_ready and data.get('ready') is not True:
        raise ValueError('Episode is a draft. Set ready to true when script and image are complete.')
    image = asset_path(path.parent, data['assets']['background'], root)
    thumbnail = data.get('assets', {}).get('thumbnail')
    if thumbnail:
        asset_path(path.parent, thumbnail, root)
    return data, image
