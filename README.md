# bg-music

A simple CLI tool to make audio sound like it's playing from speakers across a room rather than directly in your ears. Good for testing "background music" vibes for apps.

## Requirements
Python 3.11+ and these libs:
```bash
pip install pedalboard numpy scipy soundfile
```

## How to use
The main script is `bgmusic.py`. By default, it processes the input and saves a new `.wav` with the intensity in the name.

```bash
# Basic usage
python bgmusic.py song.mp3

# Custom intensity (0.0 to 1.0)
python bgmusic.py song.mp3 --intensity 0.5

# Generate an A/B comparison file (10s original / 10s processed / 10s original)
python bgmusic.py song.mp3 --ab
```

### Finding the sweet spot
If you aren't sure which intensity sounds best, use the sweep tool:

```bash
python bgmusic_sweep.py song.mp3
```
This generates 5 versions ranging from 0.2 to 1.0 intensity.

## What it actually does
The processing chain looks like this:
1. Narrow the stereo width
2. Apply a "de-presence" EQ (cuts 3kHz, high shelf cut, low-end tighten)
3. Add room reverb
4. Gentle compression to smooth out transients
5. Normalize and drop the level by 6dB
