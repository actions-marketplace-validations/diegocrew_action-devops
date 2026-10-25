#!/usr/bin/env bash
# Sourced helper: split_list prints each non-empty item of a comma- or
# newline-separated list on its own line, trimming surrounding whitespace.
split_list() {
  local item
  while IFS= read -r item; do
    item="${item#"${item%%[![:space:]]*}"}"
    item="${item%"${item##*[![:space:]]}"}"
    [[ -n "$item" ]] && printf '%s\n' "$item"
  done < <(tr ',' '\n' <<<"$1")
  return 0
}
