#!/usr/bin/env bash
# basic layout: 2x2 grid (CPU, Memory, Disk, Network)

WIN="basic"
T="${TMUX_SESSION:+${TMUX_SESSION}:}${WIN}"

tmux new-window ${TMUX_SESSION:+-t "$TMUX_SESSION"} -n "$WIN"
tmux split-window -h         -t "$T"       # left | right
tmux split-window -v         -t "${T}.1"   # right: top | bottom
tmux split-window -v         -t "${T}.0"   # left:  top | bottom

# Pane layout: .0=top-left .1=top-right .2=bottom-right .3=bottom-left
tmux send-keys -t "${T}.0" "lazysar client --preset cpu"           Enter
tmux send-keys -t "${T}.1" "lazysar client --preset memory"        Enter
tmux send-keys -t "${T}.2" "lazysar client --preset network_bytes" Enter
tmux send-keys -t "${T}.3" "lazysar client --preset disk_bytes"    Enter
# Add command pane at the bottom (full-width)
tmux split-window -v -l 5 -f -t "${T}.3"
tmux send-keys -t "${T}.4" "lazysar cmd" Enter
tmux select-pane -t "${T}.4"
