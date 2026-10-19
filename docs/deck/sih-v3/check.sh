#!/usr/bin/env bash
# Build pages, stamp the native chart, refresh the summary, run ppt-master's round-trip quality gate.
set -u
cd "$(dirname "$0")"
S="C:/Users/abhim/.claude/skills/ppt-master/scripts"
python3 build_visual.py || exit 1
python3 "$S/stamp_native_fallbacks.py" authoring-svg-flat --write 2>&1 | tail -2
python3 "$S/svg_authoring_view.py" authoring-svg-flat --refresh-summary 2>&1 | tail -1
python3 "$S/svg_quality_checker.py" . --roundtrip --json > validation/check.json 2> validation/check.err
echo "checker exit=$?"
tail -3 validation/check.err
