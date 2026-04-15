import argparse
import sys
import os
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Sweep intensity for background music effect.")
    parser.add_argument("input", help="Input audio file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"File not found: {args.input}")
        sys.exit(1)
        
    intensities = [0.2, 0.4, 0.6, 0.8, 1.0]
    
    base, ext = os.path.splitext(args.input)
    
    for intensity in intensities:
        output_file = f"{base}_intensity_{intensity:.1f}.wav"
        print(f"\n==============================================")
        print(f"Sweeping Intensity: {intensity:.1f}")
        print(f"==============================================")
        cmd = [
            sys.executable,
            "bgmusic.py",
            args.input,
            output_file,
            "--intensity",
            str(intensity)
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"Failed to process intensity {intensity}: {e}")

if __name__ == '__main__':
    main()
