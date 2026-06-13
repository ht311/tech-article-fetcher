#!/bin/sh
input=$(cat)

GRN='\033[32m'
YEL='\033[33m'
RED='\033[31m'
DIM='\033[2m'
CYN='\033[36m'
RST='\033[0m'

gauge() {
  pct=$1
  filled=$(awk "BEGIN{printf \"%d\", $pct * 10 / 100}")

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

remaining() {
  resets_at="$1"
  if [ -z "$resets_at" ] || [ "$resets_at" = "null" ]; then return; fi
  now=$(date +%s)
  diff=$((resets_at - now))
  if [ $diff -le 0 ]; then
    printf "解除済"
  elif [ $diff -lt 3600 ]; then
    printf "%dm" "$((diff / 60))"
  elif [ $diff -lt 86400 ]; then
    printf "%dh%dm" "$((diff / 3600))" "$((diff % 3600 / 60))"
  else
    printf "%dd%dh" "$((diff / 86400))" "$((diff % 86400 / 3600))"
  fi
}

ctx_pct=$(echo "$input"    | jq -r '.context_window.used_percentage // empty')
five_pct=$(echo "$input"   | jq -r '.rate_limits.five_hour.used_percentage // empty')
five_rst=$(echo "$input"   | jq -r '.rate_limits.five_hour.resets_at // empty')
week_pct=$(echo "$input"   | jq -r '.rate_limits.seven_day.used_percentage // empty')
week_rst=$(echo "$input"   | jq -r '.rate_limits.seven_day.resets_at // empty')

out=""
[ -n "$ctx_pct" ] && out="Ctx:$(gauge "$ctx_pct")"

if [ -n "$five_pct" ]; then
  rem=$(remaining "$five_rst")
  label="5h:$(gauge "$five_pct")"
  [ -n "$rem" ] && label="${label} ${CYN}(${rem})${RST}"
  out="${out:+$out | }${label}"
fi

if [ -n "$week_pct" ]; then
  rem=$(remaining "$week_rst")
  label="7d:$(gauge "$week_pct")"
  [ -n "$rem" ] && label="${label} ${CYN}(${rem})${RST}"
  out="${out:+$out | }${label}"
fi

printf "%b\n" "$out"
