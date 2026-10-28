# Pipeline validation

- 22 tests pass, covering Markdown compilation, image_ready Booleans, missing
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
