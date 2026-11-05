#!/usr/bin/python3
"""Translate the legacy Meteohub plot preamble for Debian's gnuplot 6.

Install as /usr/local/bin/gnuplot in the isolated ARM test guest only.
The distribution binary remains /usr/bin/gnuplot. Data and graph definitions
are not modified; each request uses its own temporary script.
"""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def translate(script: str) -> str:
    script = re.sub(
        r'(?m)^\s*set font "[^"]*"\s*$',
        'set fontpath "/usr/share/fonts/truetype/liberation"',
        script,
    )
    script = re.sub(r'(?m)^(\s*set timefmt) x(?=\s)', r'\1', script)
    script = re.sub(
        r"(?m)^(set terminal png font) 'lsans' ([0-9]+)",
        r"\1 'Liberation Sans,\2'",
        script,
    )
    script = re.sub(
        r'(?m)^(set title "(?:\\.|[^"\\])*") ([+-]?[0-9.]+,[+-]?[0-9.]+)',
        r'\1 offset \2',
        script,
    )
    # These entities are emitted by Meteohub for temperature/irradiance axes.
    script = script.replace('&#176;', '°').replace('&#178;', '²')
    return 'set encoding utf8\n' + script


def main() -> int:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        os.execv('/usr/bin/gnuplot', ['gnuplot', *sys.argv[1:]])
    os.umask(0o077)
    script = translate(Path(sys.argv[1]).read_text(encoding='utf-8'))
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', prefix='meteohub-plot-', suffix='.gp'
    ) as temporary:
        temporary.write(script)
        temporary.flush()
        return subprocess.run(['/usr/bin/gnuplot', temporary.name]).returncode


if __name__ == '__main__':
    sys.exit(main())
