import argparse
import sys
import numpy as np
import soundfile as sf
try:
    from pedalboard import (
        Pedalboard,
        Reverb,
        Compressor,
        HighShelfFilter,
        PeakFilter,
        HighpassFilter,
        Gain,
    )
except ImportError:
    print("Please install pedalboard: pip install pedalboard")
    sys.exit(1)


def ensure_stereo(audio):
    if len(audio.shape) == 1:
        return np.column_stack((audio, audio))
    elif audio.shape[1] == 1:
        return np.column_stack((audio[:, 0], audio[:, 0]))
    return audio


def calculate_levels(audio):
    # Avoid log of zero
    peak = 20 * np.log10(np.max(np.abs(audio)) + 1e-10)
    rms = 20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-10)
    return peak, rms


def reduce_stereo_width(audio, width_reduction):
    if width_reduction == 0.0:
        return audio
    left = audio[:, 0]
    right = audio[:, 1]
    center = (left + right) / 2.0
    new_left = left * (1 - width_reduction) + center * width_reduction
    new_right = right * (1 - width_reduction) + center * width_reduction
    return np.column_stack((new_left, new_right))


def apply_spectral_depresence(audio, sample_rate, intensity, presence_override=None):
    p_int = presence_override if presence_override is not None else intensity

    pb = Pedalboard(
        [
            # We use positional args safely for frequencies, gains, Q
            # PeakFilter: cutoff, gain, q
            PeakFilter(cutoff_frequency_hz=3000, gain_db=-4.0 * p_int, q=1.2),
            HighShelfFilter(cutoff_frequency_hz=6000, gain_db=-3.0 * intensity),
            PeakFilter(cutoff_frequency_hz=300, gain_db=1.5 * intensity, q=0.8),
            HighpassFilter(cutoff_frequency_hz=60),
        ]
    )

    return pb(audio.T, sample_rate).T


def apply_reverb(audio, sample_rate, wet, dry=0.75):
    pb = Pedalboard([Reverb(room_size=0.5, damping=0.7, wet_level=wet, dry_level=dry)])
    return pb(audio.T, sample_rate).T


def apply_compression(audio, sample_rate):
    pb = Pedalboard(
        [Compressor(threshold_db=-20.0, ratio=2.0, attack_ms=30.0, release_ms=200.0)]
    )
    return pb(audio.T, sample_rate).T


def apply_gain(audio, sample_rate, gain_db):
    pb = Pedalboard([Gain(gain_db=gain_db)])
    return pb(audio.T, sample_rate).T


def normalize_audio(audio):
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        return audio / max_val
    return audio


def create_ab_comparison(
    original, processed, sample_rate, segment_duration=10.0, crossfade_duration=0.5
):
    max_len = int(3 * segment_duration * sample_rate)
    orig = original[:max_len]
    proc = processed[:max_len]

    if len(orig) < max_len:
        pad = np.zeros((max_len - len(orig), orig.shape[1]))
        orig = np.vstack((orig, pad))
    if len(proc) < max_len:
        pad = np.zeros((max_len - len(proc), proc.shape[1]))
        proc = np.vstack((proc, pad))

    mix = np.zeros(len(orig))

    for i in range(len(mix)):
        t = i / sample_rate
        if t < 10.0:
            mix[i] = 0.0
        elif t < 10.0 + crossfade_duration:
            mix[i] = (t - 10.0) / crossfade_duration
        elif t < 20.0:
            mix[i] = 1.0
        elif t < 20.0 + crossfade_duration:
            mix[i] = 1.0 - (t - 20.0) / crossfade_duration
        else:
            mix[i] = 0.0

    mix = np.clip(mix, 0.0, 1.0)[:, np.newaxis]
    return orig * (1 - mix) + proc * mix


def main():
    parser = argparse.ArgumentParser(
        description="Process audio to sound like background music."
    )
    parser.add_argument("input", help="Input audio file")
    parser.add_argument("output", help="Output audio file")
    parser.add_argument(
        "--intensity", type=float, default=0.7, help="Master control 0.0-1.0"
    )
    parser.add_argument(
        "--width", type=float, default=None, help="Stereo width override 0.0-1.0"
    )
    parser.add_argument(
        "--reverb-wet", type=float, default=None, help="Reverb wet mix override 0.0-1.0"
    )
    parser.add_argument(
        "--presence", type=float, default=None, help="Presence cut override 0.0-1.0"
    )
    parser.add_argument(
        "--no-compress", action="store_true", help="Disable compression"
    )
    parser.add_argument("--level", type=float, default=-6.0, help="Final gain in dB")
    parser.add_argument(
        "--ab", action="store_true", help="Output a 30-second A/B comparison file"
    )

    args = parser.parse_args()

    print(f"Loading {args.input}...")
    audio, sr = sf.read(args.input)
    audio = ensure_stereo(audio)

    peak_in, rms_in = calculate_levels(audio)
    print(f"Input  - Peak: {peak_in:.1f} dB, RMS: {rms_in:.1f} dB")

    processed = audio.copy()

    # 1. Width
    width_val = args.width if args.width is not None else 0.4 * args.intensity
    print(f"Applying stereo width reduction: {width_val:.2f}")
    processed = reduce_stereo_width(processed, width_val)

    # 2. De-presence
    print("Applying spectral de-presence")
    processed = apply_spectral_depresence(processed, sr, args.intensity, args.presence)

    # 3. Reverb
    wet_val = args.reverb_wet if args.reverb_wet is not None else 0.25 * args.intensity
    print(f"Applying reverb: wet={wet_val:.2f}")
    processed = apply_reverb(processed, sr, wet=wet_val)

    # 4. Compression
    if not args.no_compress:
        print("Applying gentle compression")
        processed = apply_compression(processed, sr)

    # Normalizing before final level reduction
    print("Normalizing audio before final gain stage")
    processed = normalize_audio(processed)

    # 5. Level
    if args.level != 0:
        print(f"Applying final level reduction: {args.level} dB")
        processed = apply_gain(processed, sr, args.level)

    peak_out, rms_out = calculate_levels(processed)
    print(f"Output - Peak: {peak_out:.1f} dB, RMS: {rms_out:.1f} dB")

    print(f"Saving to {args.output}...")
    sf.write(args.output, processed, sr)

    if args.ab:
        # Create output path for AB
        ab_out = args.output.replace(".wav", "") + "_AB.wav"
        if ab_out == args.output:
            ab_out = args.output + "_AB.wav"

        print(f"Generating A/B comparison file: {ab_out}")
        ab_audio = create_ab_comparison(audio, processed, sr)
        sf.write(ab_out, ab_audio, sr)

    print("Done!")


if __name__ == "__main__":
    main()
