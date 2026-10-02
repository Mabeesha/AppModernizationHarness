#!/usr/bin/env bash
#
# Install the Modernization Harness into a working directory.
#
#   ./install.sh [--target <dir>] [--update] [--dry-run]
#
# Creates ./out/, drops AGENTS.md and out/INTAKE.md from their templates,
# installs the vendored agent skills (Angular, .NET) into .agents/skills/
# (GitLab Duo Agent Platform layout), and adds the harness entries to
# .gitignore. Anything it would overwrite is backed up first.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$SCRIPT_DIR/ModernizationHarness"
SKILLS_DIR="$HARNESS_DIR/skills"

# Appended to the target's .gitignore if not already covered.
GITIGNORE_HEADER="# Modernization Harness"
GITIGNORE_ENTRIES=("ModernizationHarness/" "AGENTS.md" ".agents/")

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
  --update         Before installing, run ./update-skills.sh to re-vendor the
                   official Angular and .NET skills into
                   ModernizationHarness/skills/. Rewrites files in this repo,
                   so the change shows up in git. Skills you write yourself
                   are left alone.
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

# --- refresh the vendored skills (update-skills.sh does the downloading) ----

if [ "$DO_UPDATE" -eq 1 ]; then
  update_args=()
  if [ "$DRY_RUN" -eq 1 ]; then update_args+=(--dry-run); fi
  bash "$SCRIPT_DIR/update-skills.sh" ${update_args[@]+"${update_args[@]}"}
  printf '\n'
fi

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

  if [ "$DRY_RUN" -eq 1 ]; then
    if [ "$quiet_files" -eq 0 ]; then note "(dry run) write $rel"; fi
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    if [ "$quiet_files" -eq 0 ]; then note "installed  $rel"; fi
  fi
  installed=$((installed + 1))
}

# gitignore_has <file> <entry> — true if a non-comment line already names it,
# with or without a trailing slash.
gitignore_has() {
  local file="$1" entry="${2%/}" line
  [ -f "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] || continue
    case "$line" in '#'*) continue ;; esac
    [ "${line%/}" = "$entry" ] && return 0
  done < "$file"
  return 1
}

update_gitignore() {
  local gi="$TARGET_DIR/.gitignore" entry
  local missing=()

  for entry in "${GITIGNORE_ENTRIES[@]}"; do
    if gitignore_has "$gi" "$entry"; then
      note "present    $entry"
    else
      missing+=("$entry")
    fi
  done

  if [ "${#missing[@]}" -eq 0 ]; then return; fi

  if [ "$DRY_RUN" -eq 1 ]; then
    for entry in "${missing[@]}"; do note "(dry run) append $entry"; done
    return
  fi

  local eol='\n'
  if [ -f "$gi" ]; then
    # Match whatever line ending the file already uses. (Checked with a case
    # glob, not grep — Git Bash's grep strips CR before matching.)
    case "$(head -c 4096 "$gi")" in *$'\r'*) eol='\r\n' ;; esac

    local bak="$BACKUP_ROOT/.gitignore"
    mkdir -p "$(dirname "$bak")"
    cp "$gi" "$bak"
    note "backed up  .gitignore -> .harness-backups/$STAMP/.gitignore"
    backed_up=$((backed_up + 1))
    # Separate from whatever came before, without stacking blank lines.
    [ -z "$(tail -c1 "$gi")" ] || printf "$eol" >> "$gi"
    [ -z "$(tail -c2 "$gi" | head -c1)" ] || printf "$eol" >> "$gi"
  else
    note "created    .gitignore"
  fi

  {
    printf "%s$eol" "$GITIGNORE_HEADER"
    for entry in "${missing[@]}"; do printf "%s$eol" "$entry"; done
  } >> "$gi"

  for entry in "${missing[@]}"; do note "appended   $entry"; done
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
    note "none vendored — run: ./update-skills.sh"
  fi
else
  note "none vendored — run: ./update-skills.sh"
fi

printf '\n.gitignore\n'
update_gitignore

printf '\nDone — %d file(s) written, %d backed up.\n' "$installed" "$backed_up"
if [ "$backed_up" -gt 0 ]; then printf 'Backups: %s\n' "$BACKUP_ROOT"; fi
cat <<'NEXT'

Next: fill in the six blocking questions in out/INTAKE.md (4, 5, 7, 9, 11, 12),
then start a session and say "run stage 0".
NEXT
