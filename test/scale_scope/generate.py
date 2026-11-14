"""Create a new, isolated synthetic C project exceeding the default 500-file budget."""

import argparse
from pathlib import Path
import shutil


def generate_project(output: Path, *, noise_files: int = 600) -> Path:
    """Write only to a newly created output folder; never replace existing samples."""
    if type(noise_files) is not int or not 0 <= noise_files <= 10000:
        raise ValueError("noise_files must be an integer between 0 and 10000")
    output.mkdir(parents=True, exist_ok=False)
    for directory, sample in (("app", "Consumer.c"), ("supplier", "Producer.c")):
        (output / directory).mkdir()
        shutil.copyfile(Path(__file__).parent / sample, output / directory / sample)
    (output / "noise").mkdir()
    for index in range(noise_files):
        (output / "noise" / f"Noise_{index:05}.c").write_text(
            f"int Noise_{index:05}(void) {{ return {index}; }}\n", encoding="ascii")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--noise-files", type=int, default=600)
    args = parser.parse_args()
    generate_project(args.output, noise_files=args.noise_files)
