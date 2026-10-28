import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('render', ROOT/'scripts/render_episode.py')
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'episodes/cafe_a1.json').read_text())

    def test_episode_and_all_bilingual_frames(self):
        render.validate(self.data)
        background = render.Image.open(ROOT/'cafe_two_people.png').convert('RGB').resize((1280,718))
        with tempfile.TemporaryDirectory() as tmp:
            for i,line in enumerate(self.data['lines']):
                output = Path(tmp)/f'{i}.png'
                render.draw_frame(background,self.data,line,0,output)
                with render.Image.open(output) as frame:
                    self.assertEqual(frame.size,(1280,1000))

    def test_unknown_speaker_rejected(self):
        self.data['lines'][0]['speaker']='other'
        with self.assertRaises(ValueError): render.validate(self.data)

    def test_missing_translation_rejected(self):
        self.data['lines'][0]['translation']=''
        with self.assertRaises(ValueError): render.validate(self.data)

    def test_invalid_playback_speed_rejected(self):
        for speed in (0, -1, 3):
            self.data['playback_speed'] = speed
            with self.assertRaises(ValueError): render.validate(self.data)

    def test_srt_millisecond_carry(self):
        self.assertEqual(render.srt_time(59.9996),'00:01:00,000')
        self.assertEqual(render.srt_time(3600.125),'01:00:00,125')


if __name__ == '__main__': unittest.main()
