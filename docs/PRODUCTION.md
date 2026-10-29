# Shared-scene podcast production

## One Markdown file per transcript

Every transcript defaults to `img/podcast.png`. Write only a Markdown file in
`input/`; no separate episode JSON, scene upload or image prompt is necessary.
The renderer automatically compiles internal files and fits the image without
distortion. New transcripts are ready by default; `image_ready: false` holds a draft.
An explicit legacy `image:` path is still supported.

```yaml
---
id: mein-tag-a1
title: Mein Tag
level: A1
playback_speed: 0.90
pause_seconds: 0.85
rate: +0%
karaoke: false
target_duration_seconds: [480, 600]
strict_duration: true
---
```

Add `## Dialogue` with a `Speaker | German | English` table. Use Ben and Anna,
or set `left_name` and `right_name`. The default pair is FlorianMultilingual
(left) and SeraphinaMultilingual (right), German (Germany), through Edge TTS.
Native rate implements the requested speed once; there is no second slowdown.

## Preview first

For a short review, use a distinct id such as `podcast-morgen-a1-preview`, add
`preview: true`, set `target_duration_seconds: [35, 60]`, and write a short excerpt.
Both rendering and publication reject previews longer than 60 seconds. Preview
media is stored under `previews/`, full episodes under `episodes/`. The current
sample does not generate or publish any eight-to-ten-minute production episode.

The old CLI/Actions `sample` option is a four-turn internal check and is not
published. Pull-request runs also remain unpublished.

## A1 editorial approach

Use familiar topics: morning routines, food, shopping, family, home and free time.
Build a longer podcast as a conversation with small connected subtopics, short
questions and personal answers, and useful natural repetition. Use present tense,
common separable verbs and basic ordering phrases. Avoid subordinate-clause-heavy
explanations, idioms and abstract discussion. Exactly two voices, no third narrator.
A1 captions allow at most 12 German words; A2 allows 18. Review vocabulary,
grammar and translations manually; structural limits cannot certify CEFR level.

For production, aim at 480–600 seconds and measure the rendered result. Revise
content if it falls outside the range, rather than padding with silence or looping.
The full episode will be authored after the one-minute sample is reviewed.

## GitHub Actions and R2

Commit ready Markdown transcripts to main. A changed shared image rebuilds ready
transcripts that use it; shared renderer changes rebuild all ready transcripts.
Only the current preview is ready during this trial. The old café lesson is a draft
because its former illustration was removed.

Configure these GitHub Actions secrets:

| Secret | Value |
|---|---|
| ACCESS_KEY_ID | R2 S3 access key id |
| SECRET_ACCESS_KEY | R2 S3 secret key |
| BUCKET_NAME | Destination bucket |
| S3_API | HTTPS R2 account S3 endpoint |
| PUBLIC_URL | Public bucket/domain base URL |

Never put credentials in Markdown or public files. The pipeline uses the existing
secrets, verifies local manifests and uploaded object sizes, then checks the public
video URL before announcing success. GitHub output artifacts are disabled.

Versioned media paths:

- Full episode: `episodes/<id>/<commit>/<run-id>-<attempt>/`.
- Review sample: `previews/<id>/<commit>/<run-id>-<attempt>/`.

Verified video/audio/thumbnail/manifest URLs and the preview flag are recorded in
`published/<id>.json`. Completion manifests are uploaded last. Public access must
work before the index is updated; publication failures are not reported as success.

Speech caching uses text, exact voice, rate and library version. Completed turns
are preserved even if a later turn fails. Each retry attempt has its own cache key,
so it can save additional progress without overwriting an immutable cache.

## Local checks

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/discover_episodes.py
python scripts/produce_episode.py --episode input/podcast-morgen-a1-preview.md
```

Verification checks stream durations, clipping, sentence boundaries, non-silent
turns and a complete FFmpeg decode. English translations stay at the bottom.
Simple white German bubbles point to the active speaker. There is no top banner.
Karaoke is optional and only enabled with reliable one-to-one word timestamps.
