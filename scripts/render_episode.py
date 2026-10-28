"""Render a bilingual German conversation using measured TTS word timestamps."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave
import unicodedata
from functools import lru_cache
from itertools import combinations

from PIL import Image, ImageDraw, ImageFont, ImageOps
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
W, H, SR = 1280, 720, 48000


def run(args):
    subprocess.run([str(x) for x in args], check=True, stdout=subprocess.DEVNULL)


def speaker_position(data, speaker_id):
    return data['speakers'][speaker_id].get('position', 'left' if speaker_id == 'male' else 'right')


def validate(data):
    if data.get('level') not in {'A1','A2'} or not data.get('lines'):
        raise ValueError('An A1 or A2 episode with at least one line is required.')
    speakers=data.get('speakers',{})
    if len(speakers)!=2:
        raise ValueError('Define exactly two speakers.')
    if {speaker_position(data,key) for key in speakers} != {'left','right'}:
        raise ValueError('Place one speaker on the left and one on the right.')
    for key,speaker in speakers.items():
        if not speaker.get('name') or len(speaker['name'])>24:
            raise ValueError('Speaker names must contain 1–24 characters.')
        engine=speaker.get('engine','piper')
        if engine not in {'piper','silero','edge'}:
            raise ValueError('Unsupported speaker engine.')
        if engine=='silero' and not speaker.get('silero_voice'):
            raise ValueError('Select a Silero voice.')
        if engine=='piper' and key not in {'male','female'} and not speaker.get('piper_voice'):
            raise ValueError('Named characters need an explicit piper_voice.')
    if not 0 <= data.get('pause_seconds',.65) <= 5:
        raise ValueError('Pause must be between 0 and 5 seconds.')
    if not .5 <= data.get('playback_speed',1.) <= 2.:
        raise ValueError('Playback speed must be between 0.5 and 2.0.')
    target=data.get('target_duration_seconds')
    if target is not None and (not isinstance(target,list) or len(target)!=2 or
                              not all(isinstance(n,(int,float)) for n in target) or not 0<target[0]<=target[1]<=3600):
        raise ValueError('Duration target must be [minimum, maximum] seconds, at most one hour.')
    word_limit=12 if data['level']=='A1' else 18
    for line in data['lines']:
        if line['speaker'] not in speakers:
            raise ValueError('Unknown speaker.')
        if not line['de'].strip() or not line['translation'].strip():
            raise ValueError('German text and translation are required.')
        if len(line['de'].split())>word_limit or '\n' in line['de']:
            raise ValueError(f'Keep each {data["level"]} caption short: at most {word_limit} words, one paragraph.')
    # Structural checks cannot certify CEFR level; scripts require editorial review.


async def synthesize(text, voice, rate, directory):
    key = hashlib.sha256(json.dumps([text, voice, rate, edge_tts.__version__]).encode()).hexdigest()[:20]
    mp3, meta = directory / f'{key}.mp3', directory / f'{key}.json'
    if mp3.exists() and meta.exists():
        return mp3, json.loads(meta.read_text())
    for attempt in range(3):
        words = []
        try:
            # aiohttp does not automatically read HTTPS_PROXY.
            speech = edge_tts.Communicate(text, voice, rate=rate, boundary='WordBoundary',
                                          proxy=os.getenv('HTTPS_PROXY') or os.getenv('https_proxy'))
            with mp3.with_suffix('.tmp').open('wb') as audio:
                async for chunk in speech.stream():
                    if chunk['type'] == 'audio':
                        audio.write(chunk['data'])
                    elif chunk['type'] == 'WordBoundary':
                        words.append({'text': chunk['text'], 'start': chunk['offset'] / 1e7,
                                      'end': (chunk['offset'] + chunk['duration']) / 1e7})
            if not words:
                raise RuntimeError('TTS returned no word timings; cannot produce synchronized karaoke.')
            mp3.with_suffix('.tmp').replace(mp3)
            meta.write_text(json.dumps(words, ensure_ascii=False))
            return mp3, words
        except Exception:
            mp3.with_suffix('.tmp').unlink(missing_ok=True)
            if attempt == 2:
                raise
            await asyncio.sleep(attempt + 1)


def font(size):
    return ImageFont.truetype('DejaVuSans.ttf', size)


def layout(text, f, max_width):
    rows, row = [], []
    for index, word in enumerate(text.split()):
        candidate = ' '.join([x[1] for x in row] + [word])
        if row and f.getlength(candidate) > max_width:
            rows.append(row)
            row = []
        row.append((index, word))
    if row:
        rows.append(row)
    return rows


def bubble_layout(text):
    # Balance short lines so a single final word does not make a wide banner-shaped box.
    words=list(enumerate(text.split()))
    for size in (42,40,38,36,34,32):
        f=ImageFont.truetype('DejaVuSans-Bold.ttf',size)
        line_height=size+8
        for count in (1,2,3):
            if count>len(words) or count*line_height+22>146:continue
            best=None
            for cuts in combinations(range(1,len(words)),count-1):
                points=(0,*cuts,len(words))
                rows=[words[start:end] for start,end in zip(points,points[1:])]
                widths=[f.getlength(' '.join(word for _,word in row)) for row in rows]
                if max(widths)>650:continue
                score=max(widths)+(max(widths)-min(widths))*.15
                if best is None or score<best[0]:best=(score,rows,max(widths))
            if best is not None:
                return f,best[1],round(best[2])+36,count*line_height+22,line_height
    raise ValueError('Dialogue is too long for a speech bubble. Split it into shorter caption turns.')


def draw_frame(background, data, line, active, dest):
    # The scene fills the 16:9 canvas. No title, counter, speed or speaker-name banner.
    im=ImageOps.fit(background.convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)
    d=ImageDraw.Draw(im)
    on_left=speaker_position(data,line['speaker'])=='left'
    f,rows,width,height,line_height=bubble_layout(line['de'])
    center=340 if on_left else 940
    x=max(10,min(W-width-10,round(center-width/2)))
    y=8 if on_left else 20
    # A small tail points toward the active character without crossing a face.
    tip=max(x+24,min(x+width-24,center))
    d.polygon([(tip-11,y+height-2),(tip+11,y+height-2),(tip,y+height+9)],fill='white',outline='#272727',width=2)
    d.rounded_rectangle((x,y,x+width,y+height),radius=18,fill='white',outline='#272727',width=2)
    d.polygon([(tip-8,y+height-3),(tip+8,y+height-3),(tip,y+height+6)],fill='white')
    text_y=y+11
    for row in rows:
        text_x=x+18
        for index,word in row:
            word_width=f.getlength(word)
            if index==active:
                d.rounded_rectangle((text_x-3,text_y-1,text_x+word_width+3,text_y+line_height-3),radius=5,fill='#fff1a8')
            d.text((text_x,text_y),word,font=f,fill='#101010',anchor='lt')
            text_x+=f.getlength(word+' ')
        text_y+=line_height
    # English stays at the bottom, with a soft contrast fade rather than a label bar.
    overlay=Image.new('RGBA',(W,H))
    od=ImageDraw.Draw(overlay)
    for yy in range(H-108,H):
        od.line((0,yy,W,yy),fill=(0,0,0,round(190*(yy-(H-108))/108)))
    im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    d=ImageDraw.Draw(im)
    tf=font(28)
    translated=layout(line['translation'],tf,W-64)
    if len(translated)>2:raise ValueError('Translation is too long for two bottom subtitle lines.')
    ty=H-16-34*len(translated)
    for row in translated:
        text=' '.join(word for _,word in row)
        d.text(((W-tf.getlength(text))/2,ty),text,font=tf,fill='white',stroke_width=1,stroke_fill='#202020',anchor='lt')
        ty+=34
    im.save(dest,quality=95,subsampling=0)
    with Image.open(dest) as check:check.load()


def srt_time(seconds):
    ms = round(seconds * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


@lru_cache(maxsize=4)
def load_piper(path):
    from piper import PiperVoice
    from piper.config import PiperConfig
    import onnxruntime
    options=onnxruntime.SessionOptions()
    options.intra_op_num_threads=2
    options.inter_op_num_threads=1
    voice=PiperVoice(session=onnxruntime.InferenceSession(path,sess_options=options,providers=['CPUExecutionProvider']),
                     config=PiperConfig.from_dict(json.loads(Path(path+'.json').read_text())))
    # Preserve German ç with older phoneme maps.
    phonemize=voice.phonemize
    voice.phonemize=lambda value:[list(unicodedata.normalize('NFC',''.join(p))) for p in phonemize(value)]
    return voice


def synthesize_piper(text, speaker, directory, models, model=None):
    from piper import SynthesisConfig
    model=model or ('de_DE-thorsten-medium' if speaker=='male' else 'de_DE-kerstin-low')
    path=models/(model+'.onnx')
    if not path.exists():raise RuntimeError('Download the configured Piper model before rendering.')
    key=hashlib.sha256((text+model+'piper-1.3.0-length-1.18-nfc').encode()).hexdigest()[:20]
    wav=directory/(key+'.wav')
    if not wav.exists():
        voice=load_piper(str(path))
        with wave.open(str(wav),'wb') as audio:
            voice.synthesize_wav(text,audio,SynthesisConfig(length_scale=1.18))
    return wav,[]


@lru_cache(maxsize=1)
def load_silero(path):
    import torch
    from download_silero import verified
    if not verified(Path(path)):
        raise RuntimeError('Download the verified model first: python scripts/download_silero.py')
    torch.set_num_threads(4)
    return torch.package.PackageImporter(str(path)).load_pickle('tts_models', 'model')


def synthesize_silero(text, speaker, directory, models):
    import torch
    key = hashlib.sha256(json.dumps([text, 'silero-v3-de', speaker, SR]).encode()).hexdigest()[:20]
    wav = directory / (key + '.wav')
    if not wav.exists():
        model = load_silero(str(models/'silero-v3-de.pt'))
        if speaker not in model.speakers or speaker == 'random':
            raise ValueError('Use a fixed, supported Silero speaker.')
        with torch.inference_mode():
            audio = model.apply_tts(text=text, speaker=speaker, sample_rate=SR)
        temporary = wav.with_suffix('.part')
        with wave.open(str(temporary), 'wb') as output:
            output.setparams((1, 2, SR, 0, 'NONE', 'not compressed'))
            output.writeframes((audio.numpy().clip(-1,1)*32767).astype('<i2').tobytes())
        temporary.replace(wav)
    return wav, []


async def build(args):
    data = json.loads(args.episode.read_text())
    if args.speed is not None:
        data['playback_speed'] = args.speed
    validate(data)
    speed = data.get('playback_speed', 1.0)
    data['engine'] = args.engine
    if args.sample:
        data['lines'] = data['lines'][:4]
    if not shutil.which('ffmpeg'):
        raise RuntimeError('Install ffmpeg and the DejaVu Sans fonts first.')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache = out / 'cache'
    cache.mkdir(exist_ok=True)
    frames = out / 'frames'
    frames.mkdir(exist_ok=True)
    background = Image.open(args.image).convert('RGB').resize((W,H), Image.Resampling.LANCZOS)
    preview = frames/'layout-check.jpg'
    for line in data['lines']:
        draw_frame(background,data,line,-1,preview)
    preview.unlink(missing_ok=True)
    timeline, frame_list, german, translations = [], [], [], []
    cursor = .0
    audio_position = 0
    # Finalize the PCM master only after every turn has generated successfully.
    pcm_parts=[]
    for number, line in enumerate(data['lines'],1):
        print(f"[{number}/{len(data['lines'])}] {line['speaker']}: {line['de']}", flush=True)
        speaker = data['speakers'][line['speaker']]
        engine = speaker.get('engine', 'piper') if args.engine == 'auto' else args.engine
        if engine == 'piper':
            voice_id = speaker.get('piper_voice')
            mp3, words = synthesize_piper(line['de'], line['speaker'], cache, args.models, voice_id)
        elif engine == 'silero':
            voice_id = speaker['silero_voice']
            mp3, words = synthesize_silero(line['de'], voice_id, cache, args.models)
        elif engine == 'edge':
            voice_id = speaker['voice']
            mp3, words = await synthesize(line['de'], voice_id, data['rate'], cache)
        else:
            raise ValueError(f'Unsupported speech engine: {engine}')
        wav = cache / (mp3.stem + f'-48k-{speed:.4f}.wav')
        run(['ffmpeg','-v','error','-y','-i',mp3,'-af',f'atempo={speed}','-ac','1','-ar',SR,'-c:a','pcm_s16le',wav])
        with wave.open(str(wav),'rb') as audio:
            pcm = audio.readframes(audio.getnframes())
        duration = len(pcm) / (SR*2)
        words = [{**w, 'start':w['start']/speed, 'end':w['end']/speed} for w in words]
        if any(w['start'] < 0 or w['end'] > duration+.1 for w in words):
            raise ValueError('TTS word timing is outside the audio.')
        # Compare word order to avoid highlighting the wrong word silently.
        normalize = lambda s: re.sub(r'[^\w]', '', s).casefold()
        if words and [normalize(w['text']) for w in words] != [normalize(w) for w in line['de'].split()]:
            raise ValueError('TTS tokenization differs from script; use sentence captions or adjust script.')
        pause_samples = round(data.get('pause_seconds', .65)*SR)
        total = duration + pause_samples/SR
        pcm_parts.append(pcm + bytes(pause_samples*2))
        events = [(0,-1)] + [(w['start'],i) for i,w in enumerate(words)] + ([(min(words[-1]['end'], duration),-1)] if words else []) + [(total,None)]
        for i, ((start, active), (end,_)) in enumerate(zip(events,events[1:])):
            if end <= start:
                continue
            path = frames / f'{number:03}-{i:03}.jpg'
            draw_frame(background,data,{**line,'_turn':number,'_total':len(data['lines'])},active,path)
            frame_list += [f"file '{path.as_posix()}'", f'option framerate {SR}', f'duration {end-start:.8f}']
        timeline.append({**line,'tts_engine':engine,'voice_id':voice_id,'start':cursor,'speech_end':cursor+duration,'end':cursor+total,
                         'words':[{**w,'start':w['start']+cursor,'end':w['end']+cursor} for w in words]})
        for entries, text in [(german,line['de']),(translations,line['translation'])]:
            entries.append(f'{number}\n{srt_time(cursor)} --> {srt_time(cursor+total)}\n{text}\n')
        audio_position += len(pcm)//2 + pause_samples
        cursor = audio_position/SR
    with wave.open(str(out/'podcast.part.wav'),'wb') as combined:
        combined.setparams((1,2,SR,0,'NONE','not compressed'))
        combined.writeframes(b''.join(pcm_parts))
    pcm_parts.clear()
    (out/'podcast.part.wav').replace(out/'podcast.wav')
    # concat requires a repeated final image for its last duration.
    frame_list.extend([frame_list[-3],f'option framerate {SR}'])
    (out/'frames.txt').write_text('\n'.join(frame_list)+'\n')
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',out/'frames.txt','-i',out/'podcast.wav',
         '-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p',
         '-r','24','-c:a','aac','-b:a','192k','-t',f'{cursor:.8f}','-movflags','+faststart',out/'podcast.mp4'])
    run(['ffmpeg','-v','error','-y','-i',out/'podcast.wav','-c:a','libmp3lame','-b:a','192k',out/'podcast.mp3'])
    (out/'german.srt').write_text('\n'.join(german),encoding='utf-8')
    (out/'translation.srt').write_text('\n'.join(translations),encoding='utf-8')
    (out/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'episode.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Done: {out / "podcast.mp4"} ({cursor:.2f}s)',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode', type=Path, default=ROOT/'episodes/cafe_a1.json')
    parser.add_argument('--image', type=Path, default=ROOT/'cafe_two_people.png')
    parser.add_argument('--output', type=Path, default=ROOT/'output/cafe')
    parser.add_argument('--engine', choices=['auto','edge','piper'], default='auto')
    parser.add_argument('--models', type=Path, default=ROOT/'models')
    parser.add_argument('--speed', type=float, help='Pitch-preserving speed multiplier; overrides episode playback_speed.')
    parser.add_argument('--sample',action='store_true',help='Render the first four turns.')
    asyncio.run(build(parser.parse_args()))
