#!/usr/bin/env bash
#
# Install the Modernization Harness into a working directory.
#
#   ./install.sh [--target <dir>] [--update] [--dry-run]
#
# Creates ./out/, drops AGENTS.md and out/INTAKE.md from their templates, and
# installs the bundled agent skills into .agents/skills/ (GitLab Duo Agent
# Platform layout). Anything it would overwrite is backed up first.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$SCRIPT_DIR/ModernizationHarness"
SKILLS_DIR="$HARNESS_DIR/skills"
MANIFEST="$SKILLS_DIR/.upstream-angular"

ANGULAR_REPO="https://github.com/angular/skills"
ANGULAR_TARBALL="https://codeload.github.com/angular/skills/tar.gz/refs/heads/main"

TARGET_DIR="$PWD"
DO_UPDATE=0
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT=""
backed_up=0
installed=0
quiet_files=0

usage() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'USAGE'

Options:
  --target <dir>   Where to install. Default: the current directory.
  --update         Before installing, re-vendor the official Angular skills from
                   github.com/angular/skills into ModernizationHarness/skills/.
                   Rewrites files in this repo, so the change shows up in git.
                   Only directories listed in skills/.upstream-angular are
                   replaced; skills you write yourself are left alone.
  --dry-run        Print what would happen; change nothing.
  -h, --help       This text.
USAGE
}

die()  { printf 'error: %s\n' "$1" >&2; exit 1; }
note() { printf '  %s\n' "$1"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target)   [ $# -ge 2 ] || die "--target needs a directory"; TARGET_DIR="$2"; shift 2 ;;
    --target=*) TARGET_DIR="${1#*=}"; shift ;;
    --update)   DO_UPDATE=1; shift ;;
    --dry-run)  DRY_RUN=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

[ -d "$HARNESS_DIR" ] || die "no ModernizationHarness/ next to this script ($HARNESS_DIR)"

# --- re-vendor the official Angular skills ---------------------------------

vendored_skills() {
  [ -f "$MANIFEST" ] || return 0
  grep '^skill=' "$MANIFEST" | cut -d= -f2-
}

update_angular_skills() {
  command -v curl >/dev/null 2>&1 || die "--update needs curl on PATH"
  command -v tar  >/dev/null 2>&1 || die "--update needs tar on PATH"

  printf 'Re-vendoring the official Angular skills from %s\n' "$ANGULAR_REPO"
  if [ "$DRY_RUN" -eq 1 ]; then note "(dry run) would rewrite $SKILLS_DIR"; return; fi

  local tmp; tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN

  curl -fsSL "$ANGULAR_TARBALL" -o "$tmp/skills.tar.gz" \
    || die "download failed — leaving the vendored copies alone"
  [ -s "$tmp/skills.tar.gz" ] || die "downloaded an empty archive — leaving the vendored copies alone"
  tar -xzf "$tmp/skills.tar.gz" -C "$tmp" || die "could not extract the archive"

  local root
  root="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'skills-*' | head -1)"
  [ -n "$root" ] || die "unexpected archive layout — no skills-* directory"

  # Drop only what we vendored last time; hand-written skills stay.
  local old
  while IFS= read -r old; do
    [ -n "$old" ] || continue
    rm -rf "${SKILLS_DIR:?}/$old"
    note "removed    skills/$old (will be replaced)"
  done < <(vendored_skills)

  mkdir -p "$SKILLS_DIR"
  local names=() name count
  for dir in "$root"/*/; do
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    cp -R "$dir" "$SKILLS_DIR/$name"
    count="$(find "$SKILLS_DIR/$name" -type f | wc -l | tr -d ' ')"
    note "vendored   skills/$name ($count file(s))"
    names+=("$name")
  done
  [ "${#names[@]}" -gt 0 ] || die "the archive contained no SKILL.md directories"

  local commit='unknown' built='unknown'
  if [ -f "$root/BUILD_INFO" ]; then
    built="$(sed -n '1p' "$root/BUILD_INFO")"
    commit="$(sed -n '2p' "$root/BUILD_INFO")"
  fi

  {
    printf '# Directories in this folder vendored from %s\n' "$ANGULAR_REPO"
    printf '# Refresh with ./install.sh --update (or .\install.ps1 -Update). Do not hand-edit.\n'
    printf 'source=%s\n' "$ANGULAR_REPO"
    printf 'ref=main\n'
    printf 'commit=%s\n' "$commit"
    printf 'built=%s\n' "$built"
    for name in "${names[@]}"; do printf 'skill=%s\n' "$name"; done
  } > "$MANIFEST"
  note "manifest   skills/.upstream-angular (upstream commit ${commit:0:12})"
}

if [ "$DO_UPDATE" -eq 1 ]; then update_angular_skills; fi

# --- install ---------------------------------------------------------------

mkdir -p "$TARGET_DIR" 2>/dev/null || true
[ -d "$TARGET_DIR" ] || die "target is not a directory: $TARGET_DIR"
TARGET_DIR="$(cd -- "$TARGET_DIR" && pwd)"
BACKUP_ROOT="$TARGET_DIR/.harness-backups/$STAMP"

# install_file <src> <dst-absolute>
install_file() {
  local src="$1" dst="$2" rel="${2#$TARGET_DIR/}"
  [ -f "$src" ] || die "template missing: $src"

  if [ -f "$dst" ]; then
    if cmp -s "$src" "$dst"; then
      if [ "$quiet_files" -eq 0 ]; then note "unchanged  $rel"; fi
      return
    fi
    local bak="$BACKUP_ROOT/$rel"
    if [ "$DRY_RUN" -eq 1 ]; then
      note "(dry run) $rel -> backup, then overwrite"
    else
      mkdir -p "$(dirname "$bak")"
      mv "$dst" "$bak"
      note "backed up  $rel -> .harness-backups/$STAMP/$rel"
      backed_up=$((backed_up + 1))
    fi
  fi

  if [ "$DRY_RUN" -eq 1 ]; then note "(dry run) write $rel"; else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    if [ "$quiet_files" -eq 0 ]; then note "installed  $rel"; fi
  fi
  installed=$((installed + 1))
}

printf 'Installing the Modernization Harness into %s\n\n' "$TARGET_DIR"

printf 'Artifact directory\n'
if [ ! -d "$TARGET_DIR/out" ]; then
  if [ "$DRY_RUN" -eq 1 ]; then note "(dry run) mkdir $TARGET_DIR/out"; else mkdir -p "$TARGET_DIR/out"; fi
fi
note "out/"

printf '\nProject files\n'
install_file "$HARNESS_DIR/AGENTS_TEMPLATE.md"   "$TARGET_DIR/AGENTS.md"
install_file "$HARNESS_DIR/0_INTAKE_TEMPLATE.md" "$TARGET_DIR/out/INTAKE.md"

printf '\nAgent skills (.agents/skills — GitLab Duo layout)\n'
if [ -d "$SKILLS_DIR" ]; then
  found=0
  for skill_dir in "$SKILLS_DIR"/*/; do
    [ -d "$skill_dir" ] || continue
    if [ ! -f "$skill_dir/SKILL.md" ]; then
      printf '  skipped    %s (no SKILL.md)\n' "$(basename "$skill_dir")"
      continue
    fi
    found=1
    name="$(basename "$skill_dir")"
    n=0
    before=$installed
    quiet_files=1
    while IFS= read -r file; do
      rel="${file#$skill_dir}"
      install_file "$file" "$TARGET_DIR/.agents/skills/$name/$rel"
      n=$((n + 1))
    done < <(find "$skill_dir" -type f | sort)
    quiet_files=0
    written=$((installed - before))
    if [ "$written" -eq 0 ]; then
      note "unchanged  .agents/skills/$name/ ($n file(s))"
    else
      note "installed  .agents/skills/$name/ ($n file(s), $written written)"
    fi
  done
  if [ "$found" -ne 1 ]; then
    note "none vendored — run: ./install.sh --update"
  fi
else
  note "none vendored — run: ./install.sh --update"
fi

printf '\nDone — %d file(s) written, %d backed up.\n' "$installed" "$backed_up"
if [ "$backed_up" -gt 0 ]; then printf 'Backups: %s\n' "$BACKUP_ROOT"; fi
cat <<'NEXT'

Next: fill in the six blocking questions in out/INTAKE.md (4, 5, 7, 9, 11, 12),
then start a session and say "run stage 0".
NEXT
