"""Compile one human-editable Markdown lesson into the renderer's internal data."""
import copy
import csv
from pathlib import Path
import re
import yaml

DEFAULT_SPEAKERS={
    'male':{'name':'Ben','position':'left','engine':'edge','piper_voice':'de_DE-thorsten-medium','voice':'de-DE-FlorianMultilingualNeural'},
    'female':{'name':'Anna','position':'right','engine':'edge','silero_voice':'eva_k','piper_voice':'de_DE-kerstin-low','voice':'de-DE-SeraphinaMultilingualNeural'},
}


def read_markdown(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    match=re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)\Z',text,re.S)
    if not match:
        raise ValueError('Markdown lessons need YAML settings between --- lines at the top.')
    metadata=yaml.safe_load(match[1])
    if not isinstance(metadata,dict):raise ValueError('Markdown settings must be a mapping.')
    if type(metadata.get('image_ready')) is not bool:
        raise ValueError('Set image_ready to true or false (without quotation marks).')
    if 'strict_duration' in metadata and type(metadata['strict_duration']) is not bool:
        raise ValueError('strict_duration must be true or false without quotes.')
    data={**metadata,'ready':metadata['image_ready']}
    data.setdefault('translation_language','English')
    data.setdefault('rate','+0%')
    data.setdefault('playback_speed',.9)
    data.setdefault('pause_seconds',.8)
    speakers=copy.deepcopy(metadata.get('speakers',DEFAULT_SPEAKERS))
    if 'speakers' not in metadata:
        speakers['male']['name']=metadata.get('left_name','Ben')
        speakers['female']['name']=metadata.get('right_name','Anna')
    data['speakers']=speakers
    names={key.casefold():key for key in speakers}
    for key,person in speakers.items():
        name=person['name'].casefold()
        if name in names and names[name]!=key:raise ValueError('Speaker names must be distinct.')
        names[name]=key
    data['assets']={'background':metadata.get('image','')}
    if metadata.get('thumbnail'):data['assets']['thumbnail']=metadata['thumbnail']
    data['lines']=[]
    if not data['ready']:return data
    in_dialogue=False
    for row in match[2].splitlines():
        if row.startswith('## '):
            in_dialogue=row[3:].strip().casefold()=='dialogue'
            continue
        if not in_dialogue or not row.strip():continue
        if not row.lstrip().startswith('|'):
            raise ValueError('Under ## Dialogue, use the Speaker | German | English table.')
        cells=[cell.strip() for cell in next(csv.reader([row.strip().strip('|')],delimiter='|',escapechar='\\'))]
        if len(cells)!=3:raise ValueError('Each dialogue row needs exactly three cells.')
        if cells[0].casefold() in {'speaker','sprecher'} or all(re.fullmatch(r':?-+:?',c) for c in cells):continue
        speaker=names.get(cells[0].casefold())
        if speaker is None:raise ValueError(f'Unknown dialogue speaker: {cells[0]}')
        data['lines'].append({'speaker':speaker,'de':cells[1],'translation':cells[2]})
    if data['ready'] and not data['lines']:raise ValueError('A ready lesson needs dialogue.')
    return data
