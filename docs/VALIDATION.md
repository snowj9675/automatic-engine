# Pipeline validation

- 23 tests pass, covering Markdown compilation, image_ready Booleans, missing
  artwork, named speakers, A2, discovery, R2 secret aliases, bucket endpoint
  normalization, public-link metadata, credential exclusion and transfer failures.
- The authored café lesson has 153 turns and renders locally to **516.81 seconds
  (8:37)**. Both encoded streams, every non-silent spoken turn, subtitle/timeline
  alignment and full FFmpeg decoding pass. Its strict 480–600 second target passes.
- The still-image concat clock now uses the audio sample timebase to prevent
  cumulative caption drift. The PCM master is finalized after all turns succeed.
- GitHub artifact upload steps are removed. The live workflow uses the configured
  R2 secrets, checks uploaded sizes and public video access, and only then writes
  intended-public links to published/<episode-id>.json. The publication index is
  the source of truth for completed live deliveries.
- An earlier 548.39-second renderer stress test used repeated sample dialogue;
  it is not the authored café lesson now being published.
- Structural/ASR checks do not certify CEFR proficiency or flawless pronunciation.

- The first live R2 transfer stored the complete 521.08-second video. Public
  browser-style HEAD returned 200 with the expected 23,092,507-byte length;
  range GET returned 206. The generic Python user agent was rejected with 403,
  so the normal public check now uses an identified browser-compatible agent
  and byte-range fallback. Verified links are recorded in the publication index.

## Female audio stability revision

The reported passage at 4:51–4:55 includes Anna’s “Danke, Ben! Guten Appetit!”
starting at 293.074 seconds in the previous published render. None of the 76
saved raw female turns contains full-scale clipping. Three fresh 48 kHz
syntheses were byte-identical to their cached originals, including the first
call after model loading; a cold-start explanation was not reproduced.

The revised path uses Silero’s 24 kHz vocoder branch and native SSML speed
control (90%). This changes synthesis rather than trying to hide crackle with
heavy denoising. Final resampling and tempo processing stay floating-point
until peak-safe PCM conversion. All turns receive 5 ms boundary fades.
Female cache keys include the new processing version and synthesis speed.

All 76 female turns were synthesized locally with the new settings. 28 tests
pass, including invalid-waveform rejection, peak-preserving conversion, SSML
escaping, independent speed caches and a real FFmpeg check that native-speed
audio is not slowed twice. The production verifier now writes per-turn
`audio-quality.json` and rejects clipped or discontinuous PCM boundaries.
These tests do not certify perceptual quality or flawless pronunciation.

## Edge Florian / Seraphina trial

The default pair is now `de-DE-FlorianMultilingualNeural` and
`de-DE-SeraphinaMultilingualNeural`, using edge-tts 7.3.1. A live request to each
voice returned audio and word boundaries. Native rate -10% implements the
requested 0.90 speed once, with no second time-stretch pass.

A four-turn preview includes the first male/female exchange, the previously
reported “Danke, Ben! Guten Appetit!” and a longer female caption. Its 19.12 s
audio/video passed full verification. Whisper-small, German, no prompt,
transcribed all 19 words of its three Seraphina turns without word errors.
This is an intelligibility test, not a perceptual quality certificate.

The trial exposed two integration issues: irregular still-frame durations could
leave a short final video tail, and a karaoke-only tokenization constraint was
being applied to sentence captions. Explicit frame-rate conversion with final
frame hold now covers the measured audio exactly. Provider boundary groups are
recorded separately from exact whitespace word matches; word highlighting still
requires an exact match. Both cases have regression coverage.
