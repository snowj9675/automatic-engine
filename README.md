# German A1 café podcast

Generate a conversation video from `cafe_two_people.png`: Ben speaks on the left,
Anna on the right. Only the current speaker's bubble appears, with word-by-word
highlighting from the voice service's real timestamps. English translations stay
in a separate bottom band. The illustration itself is static (no lip sync).

## Watch a sample on GitHub

Open **Actions → German A1 podcast** and open the latest successful run. Download
**german-a1-cafe**, unzip it, and play `podcast.mp4` or `podcast.mp3`. Branch pushes
and relevant pull requests generate four turns. After merging, **Run workflow**
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
python scripts/verify_output.py output/cafe
```

Remove `--sample` for the complete episode. Output: MP4 video, MP3 audio, WAV
master, separate German/English SRT subtitles, episode JSON, and a word-level
timeline JSON. The renderer uses 48 kHz mono audio, 24 fps video and 0.65-second
turn-taking pauses. Speech defaults to 15% slower than normal.

## Voices and timing

[edge-tts](https://github.com/rany2/edge-tts) accesses Microsoft's online Edge TTS
service. The default German neural voices are `de-DE-ConradNeural` (Ben) and
`de-DE-KatjaNeural` (Anna). It needs internet access, but no API key. Availability
and voice quality depend on the external service; this is not an uptime-guaranteed
production speech API. Check applicable service terms for your intended use.

Every turn is generated separately and cached by text, voice, rate and library
version. WordBoundary events drive the highlight. Audio is decoded before measuring
duration, and all turn offsets are assembled from exact PCM sample counts. The
renderer checks that returned tokens match the script rather than estimating
karaoke timing from word length. Delete `output/cafe/cache` to regenerate voices.
`HTTPS_PROXY` is supported when required by your network.

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
