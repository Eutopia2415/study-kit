#!/usr/bin/env python3
"""File and transcribe a class recording, for any subject.

    python3 transcribe_recording.py <audio file> <slug> --out "<subject folder>/recordings" [--date YYYY-MM-DD]

Creates <out>/<slug>_<date>/ with source.<ext> (a copy; the original is left where it was),
transcript.raw.json, transcript.raw.txt ([start-end] lines) and provenance.json. Runs the cached
local MLX Whisper large-v3-turbo model (temperature 0, no previous-text conditioning, which avoids
the repetition loops seen in earlier runs). No audio leaves this Mac. Afterwards the chat writes
NOTES.md itself (see the subject's CLAUDE.md).
"""
import argparse, datetime, hashlib, json, pathlib, shutil, subprocess, sys, time


def duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True).stdout
        return round(float(out.strip()), 1)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("slug", help="short topic slug, e.g. concavity_3_4")
    ap.add_argument("--out", required=True, help='output root, usually "<subject folder>/recordings"')
    ap.add_argument("--date", default=None, help="class date YYYY-MM-DD (default: today)")
    a = ap.parse_args()
    src = pathlib.Path(a.audio).expanduser()
    if not src.exists():
        sys.exit(f"no such file: {src}")
    day = a.date or datetime.date.today().isoformat()
    out = pathlib.Path(a.out).expanduser() / f"{a.slug}_{day.replace('-', '_')}"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / ("source" + src.suffix.lower())
    if not dst.exists():
        shutil.copy2(src, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    import mlx_whisper
    t0 = time.time()
    r = mlx_whisper.transcribe(str(dst), path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                               temperature=0.0, condition_on_previous_text=False, verbose=False)
    (out / "transcript.raw.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    with open(out / "transcript.raw.txt", "w") as f:
        for seg in r["segments"]:
            f.write(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text'].strip()}\n")
    prov = {"received_date": datetime.date.today().isoformat(), "class_date": day, "source_name": src.name,
            "source_path": str(src), "duration_seconds": duration(dst), "sha256": sha,
            "raw_asr": {"engine": "mlx_whisper", "model": "mlx-community/whisper-large-v3-turbo", "language": "en",
                        "temperature": 0, "condition_on_previous_text": False, "segments": len(r["segments"]),
                        "speaker_diarization": False, "seconds_to_run": round(time.time() - t0)}}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2))
    print(f"folder: {out}\nsegments: {len(r['segments'])}, duration: {prov['duration_seconds']}s, took {prov['raw_asr']['seconds_to_run']}s")


if __name__ == "__main__":
    main()
