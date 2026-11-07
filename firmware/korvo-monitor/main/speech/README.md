# Speech samples (not shipped in this repository)

The default public build embeds no speech. Event feedback uses a short tone
unless a valid sample for that event is present at `/sdcard/flockinator/audio/`.
This is a functional build without generated voice assets; no substitute or
silent PCM files are needed.

For speech, supply these ten samples: `takeoff.pcm`, `seen.pcm`,
`friend.pcm`, `target.pcm`, `engage.pcm`, `assign.pcm`, `share.pcm`,
`rtb.pcm`, `crash.pcm`, `kill.pcm`. Either put them on SD at the path above,
or put them in this directory and enable `CONFIG_KORVO_EMBED_SPEECH` through
**Korvo monitor → Embed operator-supplied speech samples** in
`idf.py --preview menuconfig`. With that option enabled, the build requires
all ten files and embeds them via `EMBED_FILES` in `../CMakeLists.txt`.

They are excluded from the public tree because the originals were
generated with a platform text-to-speech voice whose output terms are
the operator's to evaluate. Generate your own in the same format:

- Raw signed 16-bit little-endian PCM, mono, 16 kHz.
- At most three seconds each; keep levels modest (the reference set was
  attenuated to about 20% before conversion).
- Any short spoken phrase per event works. The state-to-file mapping is in
  `../feedback.c` (`samples`): takeoff 27, seen 2, friend 22, target 23,
  engage 6, assign 15, share 3, rtb 18, crash 9 and kill 8.

Example (macOS `say` + `ffmpeg`; any TTS + converter is equivalent):

```sh
say -v Karen -r 175 -o seen.aiff "Contact spotted"
ffmpeg -i seen.aiff -af volume=0.2 -f s16le -ac 1 -ar 16000 seen.pcm
```

With embedding enabled, the firmware copies missing defaults to
`/sdcard/flockinator/audio/` when it mounts the card; existing files are preserved.
Samples on the card can be replaced without reflashing. Missing, invalid or
unreadable samples fall back to tones. The firmware does not format a card that
fails to mount. Evaluate the voice provider's terms before distributing samples.
