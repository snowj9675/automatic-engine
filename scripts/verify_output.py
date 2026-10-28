"""Check real output streams and that subtitle/audio/video durations agree."""
import json
from pathlib import Path
import subprocess
import sys
import array
import wave
import math


def verify(folder):
    timeline = json.loads((folder/'timeline.json').read_text())
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(folder/'podcast.mp4')]))
    assert {s['codec_type'] for s in probe['streams']} == {'audio','video'}
    video = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height']) == (1280,720)
    assert abs(float(probe['format']['duration'])-timeline[-1]['end']) < .15
    for stream in probe['streams']:
        assert abs(float(stream['duration'])-timeline[-1]['end']) < .15, 'Incomplete or misaligned media stream'
    episode = json.loads((folder/'episode.json').read_text())
    with wave.open(str(folder/'podcast.wav'), 'rb') as audio:
        samples = array.array('h', audio.readframes(audio.getnframes()))
        sample_rate = audio.getframerate()
    quality=[]
    for i,line in enumerate(timeline):
        assert line['start'] < line['speech_end'] < line['end']
        assert not episode.get('karaoke',False) or line.get('tts_engine', episode['engine']) != 'edge' or line['words']
        pcm = samples[round(line['start']*sample_rate):round(line['speech_end']*sample_rate)]
        peak=max(abs(x) for x in pcm) if pcm else 0
        assert pcm and peak > 100, 'Silent speech turn'
        clipped=sum(abs(x)>=32767 for x in pcm)
        assert clipped == 0, f'Clipped speech in turn {i+1}'
        assert abs(pcm[0]) <= 32 and abs(pcm[-1]) <= 32, f'Non-zero speech boundary in turn {i+1}'
        quality.append({'turn':i+1,'speaker':line['speaker'],'peak_dbfs':round(20*math.log10(peak/32768),2),
                        'clipped_samples':clipped,'first_sample':pcm[0],'last_sample':pcm[-1]})
        assert not episode.get('karaoke',False) or not line['words'] or len(line['words']) == len(line['de'].split())
        if i:
            assert abs(line['start']-timeline[i-1]['end']) < 1e-6
        assert all(line['start'] <= w['start'] < w['end'] <= line['speech_end']+.1 for w in line['words'])
    for name in ['german.srt','translation.srt','podcast.mp3']:
        assert (folder/name).stat().st_size > 0
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(folder/'podcast.mp4'),'-f','null','-'], check=True)
    (folder/'audio-quality.json').write_text(json.dumps({'checks':'Non-silence, no clipping, boundary continuity; not a perceptual quality certification',
        'turns':quality},indent=2)+'\n')
    print(f"Verified {len(timeline)} turns, two media streams, {timeline[-1]['end']:.2f}s.")


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
