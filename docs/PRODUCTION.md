# One Markdown file per German lesson

The input format is now **one `.md` file**, with YAML settings at the top and a
German/English dialogue table below. JSON files and manifests are compiled
internally into the runner's output folder; you do not maintain them by hand.
Finished videos go to R2. **GitHub artifact uploads are disabled.**

## The normal process

1. Ask for a complete A1/A2 Markdown lesson. Save it as `input/<id>.md`, with the
   same `id` in its top settings. A draft template is in `input/_template.md`.
2. Read its scene prompt and generate the image. Upload that image into `images/`
   and set `image` to its relative path, e.g. `../images/kitchen.png`.
3. Keep `image_ready: false` while the image is missing. The workflow will wait.
4. Set `image_ready: true` and commit. The workflow validates the image and script,
   generates the entire video, verifies it, uploads it to R2 and checks public access.
5. Open `published/<id>.json` for the public video, audio, thumbnail and manifest
   links. These index files contain only intended-public delivery metadata.

The real long café lesson is `input/cafe-visit-a1.md`, using the existing image at
`images/cafe_two_people.png`. It has original continuous dialogue, not repeated
sample loops. The older folder/JSON format remains readable for compatibility,
but input examples now use Markdown exclusively.

## Settings example

```yaml
---
id: cafe-visit-a1
title: Ein Vormittag im Café
display_title: Im Café
level: A1
image_ready: true
image: ../images/cafe_two_people.png
left_name: Ben
right_name: Anna
translation_language: English
playback_speed: 0.90
pause_seconds: 0.85
target_duration_seconds: [480, 600]
strict_duration: true
thumbnail_title: Im Café · Deutsch A1
---
```

`image_ready` must be a Boolean, without quotation marks. True requires an existing
image inside the repository; false skips rendering and publication. Images are
not generated automatically. Paths are relative to the Markdown file. For an
optional finished cover, add `thumbnail: ../images/cafe-cover.png`; otherwise a
cover is made from the background and thumbnail_title.

`strict_duration: true` stops publication if measured duration is outside the
specified range. The pipeline never pads silence or repeats dialogue to force a
length. Revise the script or pacing if a draft misses its target. Its duration
report remains available on the runner for diagnosis.

## Dialogue

Use this exact section title and a three-column table:

```markdown
## Dialogue

| Speaker | German | English |
|---|---|---|
| Ben | Ich möchte einen Kaffee. | I would like a coffee. |
| Anna | Mit Milch oder ohne Milch? | With milk or without milk? |
```

Speaker names must match the two names in the settings. Default voices are
Thorsten (left, Piper) and Eva (right, Silero). Optional explicit `speakers`
settings can override voice/position details for advanced use. Keep each A1
caption to 12 German words, A2 to 18. These are layout limits, not automatic CEFR
certification. Grammar, vocabulary, translation and pronunciation still need
editorial/listening review.

Put scene ideas under `## Image prompt` and cover ideas under `## Thumbnail
prompt`. Other prose sections are authoring notes; they are not executable
pipeline instructions. The complete Markdown source is included with R2 output.

## Your GitHub Actions secrets

The workflow accepts these exact names:

| Secret | Expected value |
|---|---|
| `ACCESS_KEY_ID` | Cloudflare R2 S3 access key id |
| `SECRET_ACCESS_KEY` | R2 S3 secret access key |
| `BUCKET_NAME` | Existing bucket name |
| `S3_API` | HTTPS R2 S3 endpoint; an optional trailing `/bucket-name` is accepted |
| `PUBLIC_URL` | HTTPS public bucket/domain base URL, e.g. your `r2.dev` address |

The S3 endpoint and public URL are different. The uploader uses S3_API for signed
uploads, and PUBLIC_URL for viewer links. It never writes credentials into an
episode, generated manifest or public index. Older R2-prefixed secret names are
still accepted by the uploader for compatibility.

A complete main-branch run stores versioned objects under:

`episodes/<episode-id>/<source-commit>/<run-id>-<attempt>/`

Video, MP3, thumbnail, subtitles, script and build metadata are uploaded. The
manifest is written last. File sizes and public video access are checked before
publishing the repository index. No artifact upload or automatic video commit
is performed. Only the small public-link JSON is committed back to `published/`.
The workflow token has contents-write permission for that operation. Its index
commit does not trigger another render.

Pull requests and explicit four-turn samples do not publish. Missing/partial
credentials or a broken public URL cause publication to fail; a successful render
alone is not reported as a successful delivery. Generated files on GitHub runners
are temporary, so fix configuration errors and rerun the job if needed.

## Local tests and manual runs

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/discover_episodes.py
python scripts/produce_episode.py --episode input/cafe-visit-a1.md
```

A GitHub push of a changed ready Markdown file triggers a full render. Image
changes rebuild lessons that reference the image. Shared source changes rebuild
all ready lessons. Manual **Actions → German episode production → Run workflow**
can target an episode id; blank selects all ready lessons. Explicit short samples
are checks only and are not stored in R2. Voice models/speech are cached to speed
reruns. Caches are internal build accelerators, not viewer download artifacts.

## Layout and voices

The video fills a 1280×720 scene. Simple white speech bubbles appear above the
active character, with bold German text and bottom English subtitles. There is
no top banner or sentence/speed display. This follows the supplied conversation
reference; the earlier editorial frame and concept image are superseded.

The default voices are Edge TTS `de-DE-FlorianMultilingualNeural` (left) and
`de-DE-SeraphinaMultilingualNeural` (right). They need internet access, with no
offline model download. `playback_speed: 0.90` and base `rate: +0%` request
native -10% speech, without a second slowdown. `karaoke: false` preserves
simple sentence bubbles; real word boundaries are still saved in the timeline.
Optional older offline voices and their license details remain in the README. The pipeline can check intelligibility with the
optional ASR audit, but does not promise flawless pronunciation for every script.
