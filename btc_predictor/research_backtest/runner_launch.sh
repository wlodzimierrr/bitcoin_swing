#!/bin/bash -p
# RBT-007's only supported launch (review N2; the owner's choice of 2026-11-19).
#
# The shell (review T1; the owner's choice of 2026-11-20): started by this
# first line, bash runs privileged (-p). It reads no BASH_ENV or ENV file,
# imports no function from the environment, and ignores SHELLOPTS, BASHOPTS,
# CDPATH and GLOBIGNORE, so nothing the caller's environment names runs before
# this script. Its helpers come from bash's fixed standard path (command -p),
# never the inherited PATH. Started any other way (bash runner_launch.sh), it
# refuses. Dynamic-loader variables such as LD_PRELOAD act on any program
# before its first line; no launcher can control them.
#
# Python starts isolated (-I: no PYTHON* variable, user site or current
# directory on its path) and without site (-S: no .pth file, sitecustomize or
# usercustomize), writing no bytecode (-B) and reading an empty private
# bytecode cache, so no startup file, project import or cached bytecode runs
# before the runner's own checks. Only PATH and HOME (git reads them), LANG,
# LC_ALL, TMPDIR and the cache's name reach it. Its path is set by the fixed
# entry below: this repository, the interpreter's standard library and its
# environment's site-packages. No other Python process builds anything for it.
#
#   btc_predictor/research_backtest/runner_launch.sh run --store ~/backtest_evidence --workers N
#   btc_predictor/research_backtest/runner_launch.sh preflight
#
# RBT007_PYTHON names the interpreter; the default is this repository's .venv312.
case $- in
    *p*) ;;
    *)
        printf 'refused: start %s itself, so bash runs privileged (-p) from its first line\n' "$0" >&2
        exit 2
        ;;
esac
set -euo pipefail

repository="$(cd -- "$(command -p dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
python="${RBT007_PYTHON:-$repository/.venv312/bin/python}"
cache="$(command -p mktemp -d "${TMPDIR:-/tmp}/rbt007-pycache-XXXXXXXX")"
trap 'command -p rm -rf -- "$cache"' EXIT

entry='import sys
from pathlib import Path
repository = sys.argv.pop(1)
environment = Path(sys.executable).parent.parent
sys.path[:0] = [repository]
sys.path.append(str(environment / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" / "site-packages"))
from btc_predictor.research_backtest import runner
raise SystemExit(runner.main(sys.argv[1:]))
'

variables=("PATH=$PATH" "HOME=$HOME" "RBT007_FRESH_PYCACHE=$cache")
for name in LANG LC_ALL TMPDIR; do
    if [[ -n "${!name+set}" ]]; then
        variables+=("$name=${!name}")
    fi
done
cd -- "$repository"
status=0
command -p env -i "${variables[@]}" "$python" -I -S -B -X "pycache_prefix=$cache" -c "$entry" "$repository" "$@" || status=$?
exit "$status"
