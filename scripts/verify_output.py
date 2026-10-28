"""Check real output streams and that subtitle/audio/video durations agree."""
import json
from pathlib import Path
import subprocess
import sys


def verify(folder):
    timeline = json.loads((folder/'timeline.json').read_text())
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(folder/'podcast.mp4')]))
    assert {s['codec_type'] for s in probe['streams']} == {'audio','video'}
    video = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height']) == (1280,1000)
    assert abs(float(probe['format']['duration'])-timeline[-1]['end']) < .15
    for i,line in enumerate(timeline):
        assert line['start'] < line['speech_end'] < line['end']
        assert len(line['words']) == len(line['de'].split())
        if i:
            assert abs(line['start']-timeline[i-1]['end']) < 1e-6
        assert all(line['start'] <= w['start'] < w['end'] <= line['speech_end']+.1 for w in line['words'])
    for name in ['german.srt','translation.srt','podcast.mp3']:
        assert (folder/name).stat().st_size > 0
    print(f"Verified {len(timeline)} turns, two media streams, {timeline[-1]['end']:.2f}s.")


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
