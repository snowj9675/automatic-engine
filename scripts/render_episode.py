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

from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
W, H, SR = 1280, 1000, 48000


def run(args):
    subprocess.run([str(x) for x in args], check=True, stdout=subprocess.DEVNULL)


def validate(data):
    if data.get('level') != 'A1' or not data.get('lines'):
        raise ValueError('An A1 episode with at least one line is required.')
    if set(data['speakers']) != {'male', 'female'}:
        raise ValueError('Define male and female speakers.')
    if not 0 <= data.get('pause_seconds', .65) <= 5:
        raise ValueError('Pause must be between 0 and 5 seconds.')
    for line in data['lines']:
        if line['speaker'] not in data['speakers']:
            raise ValueError('Unknown speaker.')
        if not line['de'].strip() or not line['translation'].strip():
            raise ValueError('German text and translation are required.')
        if len(line['de'].split()) > 12 or '\n' in line['de']:
            raise ValueError('Keep each A1 turn short: at most 12 words, one paragraph.')
    # This checks structure, not CEFR proficiency. Scripts require editorial review.


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


def draw_frame(background, data, line, active, dest):
    im = Image.new('RGB', (W, H), '#101b2b')
    im.paste(background, (0, 200))
    d = ImageDraw.Draw(im)
    male = line['speaker'] == 'male'
    accent = '#70cfff' if male else '#ffc382'
    name = data['speakers'][line['speaker']]['name']
    d.text((34, 13), f"DEUTSCH A1  /  {data['title']}", font=font(19), fill='#cad7e5')
    d.text((1040, 13), f'{name} spricht', font=font(19), fill=accent)
    left, right = (32, 960) if male else (320, 1248)
    d.rounded_rectangle((left, 47, right, 177), radius=22, fill='#f8fafc', outline=accent, width=3)
    anchor = 445 if male else 910
    d.polygon([(anchor-25, 174), (anchor+25, 174), (anchor, 220)], fill='#f8fafc')
    f = font(36)
    rows = layout(line['de'], f, right-left-60)
    if len(rows) > 2:
        raise ValueError('Dialogue does not fit the speech bubble.')
    y = 64 if len(rows) == 2 else 87
    for row in rows:
        x = left + 28
        for index, word in row:
            width = f.getlength(word)
            if index == active:
                d.rounded_rectangle((x-4,y-3,x+width+5,y+44),radius=7,fill=accent)
            d.text((x, y), word, font=f, fill='#132033')
            x += f.getlength(word + ' ')
        y += 49
    d.rectangle((0, 918, W, H), fill='#101b2b')
    tf = font(28)
    rows = layout(line['translation'], tf, W-90)
    if len(rows) > 2:
        raise ValueError('Translation does not fit the bottom band.')
    for i, row in enumerate(rows):
        text = ' '.join(word for _,word in row)
        d.text(((W-tf.getlength(text))/2, 927+i*32), text, font=tf, fill='white')
    im.save(dest)


def srt_time(seconds):
    ms = round(seconds * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


async def build(args):
    data = json.loads(args.episode.read_text())
    validate(data)
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
    background = Image.open(args.image).convert('RGB').resize((1280,718), Image.Resampling.LANCZOS)
    timeline, frame_list, german, translations = [], [], [], []
    cursor = .0
    # Whole timeline is assembled in PCM; subtitle offsets use the same sample counts.
    with wave.open(str(out/'podcast.wav'), 'wb') as combined:
        combined.setparams((1,2,SR,0,'NONE','not compressed'))
        for number, line in enumerate(data['lines'],1):
            print(f"[{number}/{len(data['lines'])}] {line['speaker']}: {line['de']}", flush=True)
            mp3, words = await synthesize(line['de'], data['speakers'][line['speaker']]['voice'], data['rate'], cache)
            wav = cache / (mp3.stem + '.wav')
            run(['ffmpeg','-v','error','-y','-i',mp3,'-ac','1','-ar',SR,'-c:a','pcm_s16le',wav])
            with wave.open(str(wav),'rb') as audio:
                pcm = audio.readframes(audio.getnframes())
            duration = len(pcm) / (SR*2)
            if any(w['start'] < 0 or w['end'] > duration+.1 for w in words):
                raise ValueError('TTS word timing is outside the audio.')
            # Compare word order to avoid highlighting the wrong word silently.
            normalize = lambda s: re.sub(r'[^\w]', '', s).casefold()
            if [normalize(w['text']) for w in words] != [normalize(w) for w in line['de'].split()]:
                raise ValueError('TTS tokenization differs from script; use sentence captions or adjust script.')
            pause_samples = round(data.get('pause_seconds', .65)*SR)
            total = duration + pause_samples/SR
            combined.writeframes(pcm + bytes(pause_samples*2))
            events = [(0,-1)] + [(w['start'],i) for i,w in enumerate(words)] + [(min(words[-1]['end'], duration),-1),(total,None)]
            for i, ((start, active), (end,_)) in enumerate(zip(events,events[1:])):
                if end <= start:
                    continue
                path = frames / f'{number:03}-{i:03}.png'
                draw_frame(background,data,line,active,path)
                frame_list += [f"file '{path.as_posix()}'", f'duration {end-start:.8f}']
            timeline.append({**line,'start':cursor,'speech_end':cursor+duration,'end':cursor+total,
                             'words':[{**w,'start':w['start']+cursor,'end':w['end']+cursor} for w in words]})
            for entries, text in [(german,line['de']),(translations,line['translation'])]:
                entries.append(f'{number}\n{srt_time(cursor)} --> {srt_time(cursor+total)}\n{text}\n')
            cursor += total
    # concat requires a repeated final image for its last duration.
    frame_list.append(frame_list[-2])
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
    parser.add_argument('--sample',action='store_true',help='Render the first four turns.')
    asyncio.run(build(parser.parse_args()))
