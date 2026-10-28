"""Independent German ASR intelligibility check; this does not certify pronunciation."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import wave


def normalize(text):
    return re.findall(r'\w+', text.casefold())


def distance(expected, actual):
    previous = list(range(len(actual)+1))
    for i, word in enumerate(expected, 1):
        current = [i]
        for j, heard in enumerate(actual, 1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(word!=heard)))
        previous = current
    return previous[-1]


def audit(folder, model_name, download_root):
    from faster_whisper import WhisperModel
    timeline = json.loads((folder/'timeline.json').read_text())
    lines = [line for line in timeline if line['speaker']=='female']
    with wave.open(str(folder/'podcast.wav'), 'rb') as audio:
        rate = audio.getframerate()
        assert audio.getnchannels()==1 and audio.getsampwidth()==2
        pcm = audio.readframes(audio.getnframes())
    sample = folder/'anna-only.wav'
    with wave.open(str(sample),'wb') as audio:
        audio.setparams((1,2,rate,0,'NONE','not compressed'))
        for line in lines:
            audio.writeframes(pcm[round(line['start']*rate)*2:round(line['end']*rate)*2])
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(sample),'-b:a','192k',str(folder/'anna-only.mp3')],check=True)
    model = WhisperModel(model_name, device='cpu', compute_type='int8', cpu_threads=4,download_root=download_root)
    segments,_ = model.transcribe(str(sample),language='de',beam_size=5,temperature=0,condition_on_previous_text=False,vad_filter=False)
    heard = ' '.join(segment.text.strip() for segment in segments)
    expected = ' '.join(line['de'] for line in lines)
    tokens = normalize(expected)
    errors = distance(tokens, normalize(heard))
    report = {'test':'Automatic German intelligibility check; human listening still required',
              'model':model_name,'language':'de','prompt':None,'turns':len(lines),
              'voice_ids':sorted(set(line.get('voice_id','unknown') for line in lines)),
              'reference':expected,'transcript':heard,'reference_words':len(tokens),
              'word_errors':errors,'word_error_rate':errors/len(tokens)}
    (folder/'voice-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--model',default='small')
    parser.add_argument('--download-root',default=None)
    args=parser.parse_args()
    audit(args.folder,args.model,args.download_root)
