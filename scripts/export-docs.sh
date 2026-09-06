#!/usr/bin/env bash
# =============================================================================
#  Palisade - export the milestone documents to the Windows side
#
#  The repository lives on the Linux filesystem (~/palisade) because the
#  Windows mount is slow and does not honour Unix permission bits - see
#  docs/adr and the M0 document, section 3.3. That is the right call for the
#  code, but it makes the finished .docx files awkward to open from Windows.
#
#  This copies the generated documents out to a Windows folder so they can be
#  opened, mailed or attached without going through \\wsl$.
#
#  The repository remains the source of truth. Files here are EXPORTS: they are
#  overwritten on every run, so never edit them in place - edit
#  documentation/_build/m<N>.py and rebuild.
# =============================================================================
set -euo pipefail

DEST="${DOCS_EXPORT_DIR:-/mnt/e/PROJECTS/AIstartupDevOpsEng/documentation}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/documentation"

GREEN='\033[32m'; YEL='\033[33m'; CYA='\033[36m'; RST='\033[0m'

if [ ! -d "$(dirname "$DEST")" ]; then
  printf '  %bnote%b %s does not exist - is the drive mounted?\n' "$YEL" "$RST" "$(dirname "$DEST")"
  exit 1
fi

mkdir -p "$DEST"

printf '\n%b==>%b Exporting to %s\n' "$CYA" "$RST" "$DEST"
count=0
shopt -s nullglob
for f in "$SRC"/*.docx; do
  cp -f "$f" "$DEST/"
  printf '  %bok%b   %s\n' "$GREEN" "$RST" "$(basename "$f")"
  count=$((count+1))
done
shopt -u nullglob

if [ "$count" = "0" ]; then
  printf '  %bnote%b no .docx found in %s - build one first: cd documentation/_build && python build.py m0\n' "$YEL" "$RST" "$SRC"
  exit 1
fi

# a short note so the exported folder explains itself to anyone who finds it
cat > "$DEST/_README.txt" <<EOF
Palisade - exported milestone documentation
===========================================

These files are EXPORTS. The source of truth is the git repository at
~/palisade inside WSL2 (\\\\wsl\$\\Ubuntu-24.04\\home\\saim\\palisade).

Do not edit these files - they are overwritten by 'make docs-export'.
To change a document, edit documentation/_build/m<N>.py and rebuild:

    cd ~/palisade/documentation/_build
    python build.py m<N>
    cd ~/palisade && make docs-export

Last exported: $(date '+%Y-%m-%d %H:%M')
EOF

printf "\n  %d document(s) exported.\n\n" "$count"
