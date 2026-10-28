"""Regression checks for waveform conversion and native Silero speed control."""
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from render_episode import speech_pcm, synthesize_silero, prepare_speech, edge_rate


class SpeechAudioTests(unittest.TestCase):
    def test_invalid_synthesis_fails_before_cache_write(self):
        for data in ([], [0.,0.], [float('nan')], [float('inf')]):
            with self.assertRaises(ValueError): speech_pcm(data,24000)

    def test_overrange_speech_is_scaled_without_flattening_peaks(self):
        data=np.sin(np.arange(2000)*.04)*1.6
        pcm=np.frombuffer(speech_pcm(data,24000),dtype='<i2')
        self.assertLessEqual(int(np.abs(pcm).max()),round(.89*32767))
        ratio=pcm[120:1880]/data[120:1880]
        self.assertLess(np.std(ratio),20)
        self.assertEqual(pcm[0],0)
        self.assertEqual(pcm[-1],0)
        self.assertEqual(len(pcm),len(data))

    def test_quiet_turn_is_not_amplified(self):
        data=np.ones(1000)*.1
        pcm=np.frombuffer(speech_pcm(data,24000),dtype='<i2')
        self.assertEqual(pcm[500],round(.1*32767))

    def test_native_rate_escaped_text_and_separate_cache(self):
        class Audio:
            def numpy(self):return np.sin(np.arange(4000)*.04)*.5
        class Model:
            speakers=['eva_k']
            def apply_tts(self,**kwargs):
                calls.append(kwargs)
                return Audio()
        calls=[]
        with tempfile.TemporaryDirectory() as tmp, patch('render_episode.load_silero',return_value=Model()):
            folder=Path(tmp)
            a,_=synthesize_silero('Tee & Milch?','eva_k',folder,folder,.9)
            b,_=synthesize_silero('Tee & Milch?','eva_k',folder,folder,.9)
            c,_=synthesize_silero('Tee & Milch?','eva_k',folder,folder,1.)
            self.assertEqual(a,b)
            self.assertNotEqual(a,c)
            self.assertEqual(len(calls),2)
            self.assertIn('rate="90%"',calls[0]['ssml_text'])
            self.assertIn('Tee &amp; Milch?',calls[0]['ssml_text'])
            self.assertNotIn('text',calls[0])
            self.assertEqual(calls[0]['sample_rate'],24000)
            with wave.open(str(a)) as w:self.assertEqual(w.getframerate(),24000)


class ProcessingTests(unittest.TestCase):
    def test_native_speed_is_not_applied_twice_and_output_has_headroom(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            source=folder/'speech.wav'
            data=np.sin(2*np.pi*440*np.arange(24000)/24000)*.99
            with wave.open(str(source),'wb') as w:
                w.setparams((1,2,24000,0,'NONE',''))
                w.writeframes(np.rint(data*32767).astype('<i2').tobytes())
            for native in (True,False):
                out=folder/f'{native}.wav'
                prepare_speech(source,out,.9,native_speed=native)
                with wave.open(str(out)) as w:
                    self.assertEqual(w.getframerate(),48000)
                    duration=w.getnframes()/48000
                    pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
                self.assertAlmostEqual(duration,1. if native else 1/.9,delta=.03)
                self.assertLessEqual(int(np.abs(pcm).max()),round(.89*32767))
                self.assertEqual((pcm[0],pcm[-1]),(0,0))


class EdgeRateTests(unittest.TestCase):
    def test_native_speed_and_explicit_base_rate(self):
        self.assertEqual(edge_rate('+0%',.9),'-10%')
        self.assertEqual(edge_rate('+0%',1.),'+0%')
        self.assertEqual(edge_rate('-10%',.9),'-19%')
        for rate in ('fast','0.9','-100%'):
            with self.assertRaises(ValueError):edge_rate(rate,.9)
