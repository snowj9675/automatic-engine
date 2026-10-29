# A1 German podcast

Ben and Anna talk about everyday life in simple German. Every transcript reuses
[img/podcast.png](img/podcast.png). The scene is static, with no lip sync. German
speech bubbles follow the active speaker; English translations stay at the bottom.
The 4:3 illustration is fitted into a 1280×720 canvas without stretching or cropping.
There are no top banners, counters or speed labels.

## Review sample

[Mein Morgen](input/podcast-morgen-a1-preview.md) is a short, strictly beginner
conversation: getting up, tea, coffee and breakfast. Its explicit `preview: true`
setting limits it to one minute and publishes it to the separate `previews/` R2
prefix. Public links appear in `published/podcast-morgen-a1-preview.json` after a
successful run. This is the current trial; an 8–10 minute episode comes after review.
The old café lesson is archived as a draft and its historical R2 links remain available.

## Add a transcript

Copy [input/_template.md](input/_template.md) to `input/<episode-id>.md`, change its
id/title, and write the German/English dialogue table. No new scene image, artwork
prompt, or image_ready flag is required. The shared scene is selected automatically.

For production use `target_duration_seconds: [480, 600]`, `strict_duration: true`,
and omit `preview` (or set it to false). Keep the language A1: short present-tense
questions and answers, familiar daily words, at most 12 German words per turn.
Use exactly two speakers. Duration is measured from actual generated speech;
word counts alone cannot guarantee an eight-to-ten-minute episode. A2 is supported
when explicitly selected, with at most 18 words per caption.

A commit to main renders ready transcripts and uploads verified files to R2.
GitHub output artifacts are disabled. Previews and full episodes have distinct
storage prefixes; public links are committed under `published/`. `image_ready: false`
remains available to keep a transcript as a draft.

## Voices and audio

- Ben / left: `de-DE-FlorianMultilingualNeural` (Edge TTS).
- Anna / right: `de-DE-SeraphinaMultilingualNeural` (Edge TTS).
- Native speed 0.90×, with 0.85-second pauses in the sample.
- Full sentence bubbles by default; `karaoke: true` requires an exact provider word mapping.

Edge TTS 7.3.1 needs internet access. Temporary failures are retried with increasing
delays; completed speech turns are cached, including after a failed run. No error
silently switches voices. Audio is converted in floating point with peak headroom
and short boundary fades. The verifier checks clipping, continuity, audio/video
lengths and complete media decoding. Technical checks do not certify pronunciation.

## Run locally

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/produce_episode.py --episode input/podcast-morgen-a1-preview.md
```

Use the Markdown `preview: true` flag for a publishable one-minute review sample.
The legacy CLI `--sample` is a four-turn internal check and does not publish.

See [docs/PRODUCTION.md](docs/PRODUCTION.md) for R2 settings and delivery details.
Historical offline voice tests and their attribution remain documented in
[docs/VALIDATION.md](docs/VALIDATION.md). Optional Silero v3 German is from the
[Silero Team](https://github.com/snakers4/silero-models), licensed under
[CC BY-NC-SA 4.0](https://github.com/snakers4/silero-models/blob/master/LICENSE).
Historical Eva audio uses that noncommercial model. Piper is GPL-3.0; Thorsten's
voice dataset is CC0 per its
[model card](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/medium/MODEL_CARD).
