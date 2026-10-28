# German A1 café podcast

Generate a conversation video from `cafe_two_people.png`: Ben speaks on the left,
Anna on the right. Only the current speaker's bubble appears, with optional word-by-word
highlighting when using the Edge engine. English translations stay
in a separate bottom band. The illustration itself is static (no lip sync).

## Visual style

Warm cream and espresso framing, teal/coral speaker accents, name badges, subtle
shadows, shaped speech tails, and a dedicated English subtitle band. The header
shows the current turn and playback speed. Faces and the full café scene remain
visible.

![Café episode preview](samples/cafe-a1-preview.jpg)

## Included preview

The checked-in [31-second video](samples/cafe-a1.mp4) and [audio](samples/cafe-a1.mp3)
contain all 12 turns, rendered with Piper. Local stream/duration checks and a full
FFmpeg decode passed. English and German subtitles are also in `samples/`.

## Generate a sample on GitHub

Open **Actions → German A1 podcast** and open the latest successful run. Download
**german-a1-cafe**, unzip it, and play `podcast.mp4` or `podcast.mp3`. Relevant commits on `main` and pull requests generate four turns. After merging, **Run workflow**
lets you uncheck **sample** to render all 12 turns. Artifacts expire after 30 days.
A failed voice-service request fails the job; it never substitutes silent audio.

## Local generation

Requires Python 3.12, FFmpeg, and DejaVu Sans fonts. On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg fonts-dejavu-core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/render_episode.py --sample
# Optional override: python scripts/render_episode.py --speed 0.90
python scripts/verify_output.py output/cafe
```

Remove `--sample` for the complete episode. Output: MP4 video, MP3 audio, WAV
master, separate German/English SRT subtitles, episode JSON, and a word-level
timeline JSON. The renderer uses 48 kHz mono audio, 24 fps video and 0.65-second
turn-taking pauses. Speech plays at 0.90× the previous preview, with pitch preserved.

## Voices and timing

The default is [Piper](https://github.com/OHF-Voice/piper1-gpl), running German
neural voices locally on CPU: Thorsten (male, medium) and Kerstin (female, low).
Download once; synthesis then works offline. The female model has lower audio
fidelity than the male model, so treat this as a functional sample for review.
Piper captions are synchronized per turn, without estimated word highlighting.

```bash
python -m piper.download_voices --data-dir models de_DE-thorsten-medium de_DE-kerstin-low
python scripts/render_episode.py --sample
```

Optional `--engine edge` uses `de-DE-ConradNeural` and `de-DE-KatjaNeural` through
[edge-tts](https://github.com/rany2/edge-tts). It provides word timestamps for
karaoke highlighting and uses the episode's `rate` setting. Both local and GitHub
runner tests returned HTTP 403 with this service; it is experimental and is not
the default. No API keys are required. Piper uses a fixed 1.18 synthesis duration scale; the episode’s `playback_speed` applies a further pitch-preserving 0.90× slowdown to either engine. Word timestamps are scaled with the audio.
The workflow offers an engine selector for manual runs.

Piper software is GPL-3.0; voice dataset licenses are CC0 according to their
[Thorsten model card](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/medium/MODEL_CARD)
and [Kerstin model card](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/kerstin/low/MODEL_CARD).
Models are downloaded, not included in this repository.

Every turn is cached by text, voice and speech settings. Audio is decoded before
measuring duration; turn offsets use exact PCM sample counts. Edge mode checks
that returned word tokens match the script. Delete the output cache to regenerate
voices. Neither mode fabricates speech on a synthesis error.

## Editing the lesson

Edit `episodes/cafe_a1.json`; keep `de`, `translation`, and `speaker` for each turn.
Use `male` or `female` speaker IDs. Change `translation` to another language and
update `translation_language` if desired; font support must cover that language.
The current script is a deliberately short A1 café conversation: greetings,
coffee/tea, milk, cake, hunger and hot drinks. It uses present tense, basic questions,
`möchte` and common everyday vocabulary. `möchte` and accusative forms such as
`einen Tee` are standard beginner ordering phrases. It is a reviewed fixed script,
not unrestricted AI script generation. Structural checks cannot certify CEFR level;
review new scripts for vocabulary, grammar, pronunciation and translations.

### Episode transcript

| Speaker | German | English |
|---|---|---|
| Ben | Hallo, Anna! Wie geht es dir? | Hello, Anna! How are you? |
| Anna | Gut, danke! Und dir? | Good, thanks! And you? |
| Ben | Auch gut. Was möchtest du trinken? | Good too. What would you like to drink? |
| Anna | Ich möchte einen Tee, bitte. | I would like a tea, please. |
| Ben | Mit Milch oder ohne Milch? | With milk or without milk? |
| Anna | Ohne Milch. Und du? | Without milk. And you? |
| Ben | Ich nehme einen Kaffee mit Milch. | I will have a coffee with milk. |
| Anna | Möchtest du auch einen Kuchen? | Would you also like a cake? |
| Ben | Ja, bitte. Ich habe Hunger. | Yes, please. I am hungry. |
| Anna | Ich auch. Der Kuchen ist gut! | Me too. The cake is good! |
| Ben | Ist dein Tee heiß? | Is your tea hot? |
| Anna | Ja. Ich warte noch. | Yes. I will wait a little longer. |
