# Production pipeline validation

- 15 unit/integration tests passed: episode detection, shared artwork changes,
  draft handling, A2 named characters, asset boundaries, R2 configuration,
  file tampering, preview skipping, upload failure and manifest-last ordering.
- The complete 12-turn café package rendered and passed stream, non-silent audio,
  timing and full FFmpeg decoding checks; the fallback thumbnail was inspected.
- A **548.39-second (9:08) duration test** rendered 192 caption turns and passed
  the same media checks. It repeated the reference dialogue purely to test the
  renderer at lesson length; it is not an authored lesson or a delivered episode.
- R2 upload tests used a storage double. No live bucket upload was performed;
  real credential/bucket verification is pending setup.
- A1/A2 validation checks structure and caption length, not language proficiency
  or perfect pronunciation. Script editing and listening review remain necessary.
