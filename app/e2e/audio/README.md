# Synthetic test audio

Text-to-speech clips made on 2026-10-27 with macOS `say -v Paulina` (a built-in synthetic voice), converted with
`afconvert -f WAVE -d LEI16@16000 -c 1` (mono PCM16, 16 kHz, the format the Meta transcription API accepts), then padded with 3 s of silence so the browser's looping fake microphone says each phrase once.
No real voice is recorded here. Only this synthetic audio is sent to the Meta Model API in tests.

| File | Text |
|---|---|
| `que-tengo-pendiente.wav` | «¿Qué tengo pendiente?» |
| `abre-el-siguiente.wav` | «Abre el siguiente.» |
| `nodulo-12mm.wav` | «El nódulo mide doce milímetros.» |
