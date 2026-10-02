#!/usr/bin/env bash
#
# Refresh the agent skills vendored into ModernizationHarness/skills/.
#
#   ./update-skills.sh [--source angular|dotnet|all] [--dry-run]
#
# Downloads each trusted upstream at one exact commit and rewrites only the
# skill directories that upstream owns (listed in skills/.upstream-<source>).
# Skills you write yourself are never touched. The result is an ordinary,
# reviewable git diff in this repo.

set -euo pipefail
export LC_ALL=C   # byte-order globbing, so the manifest matches update-skills.ps1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/ModernizationHarness/skills"

# The trusted upstreams. These are fixed on purpose: there is no option to
# download from anywhere else.
#   angular  github.com/angular/skills  skills sit at the repo root
#   dotnet   github.com/dotnet/skills   skills sit under plugins/<plugin>/skills/
SOURCES=(angular dotnet)
repo_of() {
  case "$1" in
    angular) printf 'angular/skills' ;;
    dotnet)  printf 'dotnet/skills' ;;
  esac
}

# Which dotnet/skills plugins to take. Keep in step with update-skills.ps1.
DOTNET_PLUGINS=(dotnet dotnet-aspnetcore dotnet-data dotnet-test)

SOURCE=all
DRY_RUN=0

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  cat <<'USAGE'

Options:
  --source <name>  angular, dotnet, or all (default: all).
  --dry-run        Download and report what would change; write nothing.
  -h, --help       This text.
USAGE
}

die()  { printf 'error: %s\n' "$1" >&2; exit 1; }
note() { printf '  %s\n' "$1"; }

in_list() {
  local want="$1" item; shift
  for item in "$@"; do [ "$item" = "$want" ] && return 0; done
  return 1
}

# Skill names become directory names, here and in the target; keep them plain.
check_name() {
  case "$1" in
    ''|.*|*[!A-Za-z0-9._-]*) die "refusing unsafe skill name '$1'" ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --source)   [ $# -ge 2 ] || die "--source needs a value"; SOURCE="$2"; shift 2 ;;
    --source=*) SOURCE="${1#*=}"; shift ;;
    --dry-run)  DRY_RUN=1; shift ;;
    -h|--help)  usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

case "$SOURCE" in
  all) SELECTED=("${SOURCES[@]}") ;;
  angular|dotnet) SELECTED=("$SOURCE") ;;
  *) die "unknown source: $SOURCE (angular, dotnet or all)" ;;
esac

[ -d "$SKILLS_DIR" ] || die "no ModernizationHarness/skills/ next to this script ($SKILLS_DIR)"
command -v curl >/dev/null 2>&1 || die "needs curl on PATH"
command -v tar  >/dev/null 2>&1 || die "needs tar on PATH"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# HTTPS only, and no redirects: a redirect could only lead somewhere we did not name.
CURL=(curl -fsS --proto '=https' --tlsv1.2 --max-redirs 0)

# resolve_commit <owner/repo> — the commit id main points at right now.
resolve_commit() {
  local sha
  sha="$("${CURL[@]}" -H 'Accept: application/vnd.github.sha' \
          "https://api.github.com/repos/$1/commits/main")" \
    || die "could not ask GitHub which commit $1 is at — nothing was changed"
  case "$sha" in
    *[!0-9a-f]*|'') die "GitHub did not return a commit id for $1 — nothing was changed" ;;
  esac
  [ "${#sha}" -eq 40 ] || die "GitHub did not return a commit id for $1 — nothing was changed"
  printf '%s' "$sha"
}

# fetch <owner/repo> <sha> — download exactly that commit; print where it unpacked.
fetch() {
  local repo="$1" sha="$2" dir="$TMP/${1//\//_}"
  mkdir -p "$dir"
  "${CURL[@]}" "https://codeload.github.com/$repo/tar.gz/$sha" -o "$dir/src.tar.gz" \
    || die "download of $repo failed — nothing was changed"
  [ -s "$dir/src.tar.gz" ] || die "downloaded an empty $repo archive — nothing was changed"
  tar -xzf "$dir/src.tar.gz" -C "$dir" || die "could not extract the $repo archive"
  local root="$dir/${repo#*/}-$sha"
  [ -d "$root" ] || die "unexpected $repo archive layout — no ${repo#*/}-$sha directory"
  printf '%s' "$root"
}

# load_owned <source> — set OWNED to the directories that source vendored last time.
load_owned() {
  local manifest="$SKILLS_DIR/.upstream-$1" line
  OWNED=()
  [ -f "$manifest" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    case "$line" in skill=*) ;; *) continue ;; esac
    line="${line#skill=}"
    check_name "$line"
    OWNED+=("$line")
  done < "$manifest"
}

# --- 1. download and check every source before touching anything ------------

ALL_NEW=()

prepare() {
  local source="$1" repo sha root
  repo="$(repo_of "$source")"
  sha="$(resolve_commit "$repo")"
  root="$(fetch "$repo" "$sha")"
  printf '%s' "$sha"  > "$TMP/$source.sha"
  printf '%s' "$root" > "$TMP/$source.root"

  local parents=() plugin
  if [ "$source" = dotnet ]; then
    for plugin in "${DOTNET_PLUGINS[@]}"; do
      [ -d "$root/plugins/$plugin/skills" ] \
        || die "dotnet/skills has no plugin '$plugin' — fix DOTNET_PLUGINS; nothing was changed"
      parents+=("$root/plugins/$plugin/skills")
    done
  else
    parents=("$root")
  fi

  load_owned "$source"
  local old=(${OWNED[@]+"${OWNED[@]}"})

  local parent dir name found=0
  : > "$TMP/$source.plan"
  for parent in "${parents[@]}"; do
    for dir in "$parent"/*/; do
      [ -f "$dir/SKILL.md" ] || continue
      name="$(basename "$dir")"
      check_name "$name"
      if in_list "$name" ${ALL_NEW[@]+"${ALL_NEW[@]}"}; then
        die "two upstream skills are both called '$name' — nothing was changed"
      fi
      if [ -e "$SKILLS_DIR/$name" ] && ! in_list "$name" ${old[@]+"${old[@]}"}; then
        die "skills/$name already exists and did not come from $repo — rename one of them; nothing was changed"
      fi
      ALL_NEW+=("$name")
      printf '%s\t%s\n' "$name" "${dir%/}" >> "$TMP/$source.plan"
      found=1
    done
  done
  [ "$found" -eq 1 ] || die "$repo has no SKILL.md directories where expected — nothing was changed"
}

# --- 2. apply ---------------------------------------------------------------

apply() {
  local source="$1" repo sha root
  repo="$(repo_of "$source")"
  sha="$(cat "$TMP/$source.sha")"
  root="$(cat "$TMP/$source.root")"
  local manifest="$SKILLS_DIR/.upstream-$source"

  printf '\n%s — github.com/%s @ %s\n' "$source" "$repo" "${sha:0:12}"

  load_owned "$source"
  local old=(${OWNED[@]+"${OWNED[@]}"}) new=() name path
  while IFS=$'\t' read -r name path; do new+=("$name"); done < "$TMP/$source.plan"

  for name in ${old[@]+"${old[@]}"}; do
    in_list "$name" "${new[@]}" || note "removed    skills/$name (no longer upstream)"
  done

  if [ "$DRY_RUN" -eq 1 ]; then
    for name in "${new[@]}"; do
      if in_list "$name" ${old[@]+"${old[@]}"}; then note "(dry run) replace skills/$name"
      else note "(dry run) add     skills/$name"; fi
    done
    return
  fi

  for name in ${old[@]+"${old[@]}"}; do rm -rf "${SKILLS_DIR:?}/$name"; done

  local count
  while IFS=$'\t' read -r name path; do
    cp -R "$path" "$SKILLS_DIR/$name"
    count="$(find "$SKILLS_DIR/$name" -type f | wc -l | tr -d ' ')"
    note "vendored   skills/$name ($count file(s))"
  done < "$TMP/$source.plan"

  # Both upstreams are MIT, which asks that the licence travel with the copy.
  local f
  for f in LICENSE LICENSE.md LICENSE.txt; do
    if [ -f "$root/$f" ]; then cp "$root/$f" "$SKILLS_DIR/LICENSE-$source"; break; fi
  done

  {
    printf '# Skill directories in this folder vendored from https://github.com/%s\n' "$repo"
    printf '# Refresh with %s. Do not hand-edit.\n' './update-skills.sh (or .\update-skills.ps1)'
    printf 'source=https://github.com/%s\n' "$repo"
    printf 'ref=main\n'
    printf 'commit=%s\n' "$sha"
    if [ -f "$root/BUILD_INFO" ]; then printf 'built=%s\n' "$(sed -n '1p' "$root/BUILD_INFO" | tr -d '\r')"; fi
    if [ "$source" = dotnet ]; then
      for f in "${DOTNET_PLUGINS[@]}"; do printf 'plugin=%s\n' "$f"; done
    fi
    for name in "${new[@]}"; do printf 'skill=%s\n' "$name"; done
  } > "$manifest"
  note "manifest   skills/.upstream-$source"
}

printf 'Updating vendored skills in %s\n' "$SKILLS_DIR"
for s in "${SELECTED[@]}"; do prepare "$s"; done
for s in "${SELECTED[@]}"; do apply "$s"; done

if [ "$DRY_RUN" -eq 1 ]; then
  printf '\nDry run — nothing was written.\n'
else
  printf '\nDone. Review with: git diff --stat -- ModernizationHarness/skills\n'
fi
