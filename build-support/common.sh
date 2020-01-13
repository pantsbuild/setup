COLOR_RED="\x1b[31m"
COLOR_RESET="\x1b[0m"

function log() {
  echo -e "$@" 1>&2
}

function die() {
  (($# > 0)) && log "\n${COLOR_RED}$*${COLOR_RESET}"
  exit 1
}
