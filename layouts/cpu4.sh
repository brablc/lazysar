#!/usr/bin/env bash
# cpu4 layout: overall + 4 per-core CPU panes, tiled

WIN="cpu4"
T="${TMUX_SESSION:+${TMUX_SESSION}:}${WIN}"

tmux new-window ${TMUX_SESSION:+-t "$TMUX_SESSION"} -n "$WIN"
for _ in $(seq 4); do
  tmux split-window -t "$T"
done
tmux select-layout -t "$T" tiled

tmux send-keys -t "${T}.0" "lazysar client --preset cpu100"        Enter
tmux send-keys -t "${T}.1" "lazysar client --preset cpu100 -P 0"   Enter
tmux send-keys -t "${T}.2" "lazysar client --preset cpu100 -P 1"   Enter
tmux send-keys -t "${T}.3" "lazysar client --preset cpu100 -P 2"   Enter
tmux send-keys -t "${T}.4" "lazysar client --preset cpu100 -P 3"   Enter
# Add command pane at the bottom (full-width)
tmux split-window -v -l 5 -f -t "${T}.4"
tmux send-keys -t "${T}.5" "lazysar cmd" Enter
tmux select-pane -t "${T}.5"
