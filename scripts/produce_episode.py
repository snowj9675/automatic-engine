"""Render and verify one complete episode package, thumbnail and delivery manifest."""
import argparse
import asyncio
import hashlib
import json
import mimetypes
from pathlib import Path
import shutil
from types import SimpleNamespace
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
from episode_package import ROOT, load_package, asset_path
from render_episode import build, validate, font, layout
from verify_output import verify

DELIVERABLES = ['podcast.mp4','podcast.mp3','german.srt','translation.srt','timeline.json',
                'episode.json','source.json','thumbnail.png','production-report.json','audio-quality.json']


def thumbnail(data, image_path, package, destination):
    custom = data.get('assets',{}).get('thumbnail')
    if custom:
        image = ImageOps.fit(Image.open(asset_path(package,custom)).convert('RGB'),(1280,720))
    else:
        image = ImageOps.fit(Image.open(image_path).convert('RGB'),(1280,720))
        # A readable fallback cover, not an AI-generated replacement for the supplied image.
        draw=ImageDraw.Draw(image)
        draw.rounded_rectangle((28,530,1252,696),radius=24,fill='#302720')
        title=data.get('thumbnail_title',data['title'])
        rows=layout(title,font(42),1150)
        if len(rows)>2:
            raise ValueError('Thumbnail title is too long; supply a shorter thumbnail_title.')
        for index,row in enumerate(rows):
            draw.text((55,547+index*50),' '.join(word for _,word in row),font=font(42),fill='#fff8ee')
        draw.text((56,660),f"DEUTSCH {data['level']}  ·  {data.get('translation_language','English')} subtitles",font=font(17),fill='#e8d1ad')
    image.save(destination)


async def produce(path, sample=False, engine='auto'):
    data,image = load_package(path)
    validate(data)
    output=ROOT/'output'/data['id']
    output.mkdir(parents=True,exist_ok=True)
    compiled=output/'compiled.json'
    compiled.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    await build(SimpleNamespace(episode=compiled,image=image,output=output,models=ROOT/'models',
                                sample=sample,engine=engine,speed=None))
    verify(output)
    (output/'source.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    prompts=path.parent/'prompts.md'
    files=list(DELIVERABLES)
    if path.suffix=='.md':
        shutil.copyfile(path,output/'source.md')
        files.append('source.md')
    elif prompts.exists():
        shutil.copyfile(prompts,output/'prompts.md')
        files.append('prompts.md')
    thumbnail(data,image,path.parent,output/'thumbnail.png')
    timeline=json.loads((output/'timeline.json').read_text())
    duration=timeline[-1]['end']
    target=data.get('target_duration_seconds')
    on_target=None if not target or sample else target[0] <= duration <= target[1]
    report={'id':data['id'],'sample':sample,'duration_seconds':round(duration,3),
            'target_duration_seconds':target,'within_target':on_target,
            'note':'Duration is measured from generated speech. No artificial padding or repeated dialogue is added.'}
    if on_target is False:
        print('Duration is outside the requested range; revise the script after reviewing production-report.json.',flush=True)
    (output/'production-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if on_target is False and data.get('strict_duration') is True:
        raise ValueError('Episode is outside the required duration range. See production-report.json.')
    revision=os.getenv('GITHUB_SHA') or 'local'
    manifest={'id':data['id'],'revision':revision,'sample':sample,'duration_seconds':duration,'files':[]}
    for name in files:
        item=output/name
        manifest['files'].append({'name':name,'size':item.stat().st_size,
                                  'sha256':hashlib.sha256(item.read_bytes()).hexdigest(),
                                  'content_type':mimetypes.guess_type(name)[0] or 'application/octet-stream'})
    run_id=os.getenv('GITHUB_RUN_ID')
    manifest['build_id']=(run_id+'-'+os.getenv('GITHUB_RUN_ATTEMPT','1')) if run_id else hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()[:16]
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',type=Path,required=True)
    parser.add_argument('--sample',action='store_true')
    parser.add_argument('--engine',choices=['auto','piper','edge'],default='auto')
    args=parser.parse_args()
    asyncio.run(produce(args.episode.resolve(),args.sample,args.engine))
