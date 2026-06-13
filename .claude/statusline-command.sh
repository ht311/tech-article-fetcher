#!/bin/sh
input=$(cat)

GRN='\033[32m'
YEL='\033[33m'
RED='\033[31m'
DIM='\033[2m'
RST='\033[0m'

gauge() {
  pct=$1
  filled=$(awk "BEGIN{printf \"%d\", $pct * 10 / 100}")
  empty=$((10 - filled))

  if awk "BEGIN{exit !($pct >= 80)}"; then
    color=$RED
  elif awk "BEGIN{exit !($pct >= 50)}"; then
    color=$YEL
  else
    color=$GRN
  fi

  bar="${color}"
  i=0
  while [ $i -lt $filled ]; do bar="${bar}█"; i=$((i+1)); done
  bar="${bar}${DIM}"
  while [ $i -lt 10 ];      do bar="${bar}░"; i=$((i+1)); done
  bar="${bar}${RST}"

  printf "%b %.0f%%" "$bar" "$pct"
}

ctx_pct=$(echo "$input"  | jq -r '.context_window.used_percentage // empty')
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

out=""
[ -n "$ctx_pct" ]  && out="Ctx:$(gauge "$ctx_pct")"
[ -n "$five_pct" ] && out="${out:+$out | }5h:$(gauge "$five_pct")"
[ -n "$week_pct" ] && out="${out:+$out | }7d:$(gauge "$week_pct")"

echo "$out"
