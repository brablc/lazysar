#!/usr/bin/env bash
# hosts layout: 9 panes (CPU/Disk/Network x mng/node1/node2), tiled

NODE1=${NODE1:-node1}
NODE2=${NODE2:-node2}

WIN="hosts"
T="${TMUX_SESSION:+${TMUX_SESSION}:}${WIN}"

tmux new-window ${TMUX_SESSION:+-t "$TMUX_SESSION"} -n "$WIN"
for _ in $(seq 8); do
  tmux split-window -t "$T"
done
tmux select-layout -t "$T" tiled

tmux send-keys -t "${T}.0" "lazysar client --preset cpu100"                     Enter
tmux send-keys -t "${T}.1" "lazysar client --preset cpu100 --host $NODE1"       Enter
tmux send-keys -t "${T}.2" "lazysar client --preset cpu100 --host $NODE2"       Enter
tmux send-keys -t "${T}.3" "lazysar client --preset disk_bytes"                 Enter
tmux send-keys -t "${T}.4" "lazysar client --preset disk_bytes --host $NODE1"   Enter
tmux send-keys -t "${T}.5" "lazysar client --preset disk_bytes --host $NODE2"   Enter
tmux send-keys -t "${T}.6" "lazysar client --preset network_bytes"              Enter
tmux send-keys -t "${T}.7" "lazysar client --preset network_bytes --host $NODE1" Enter
tmux send-keys -t "${T}.8" "lazysar client --preset network_bytes --host $NODE2" Enter
# Add command pane at the bottom (full-width)
tmux split-window -v -l 5 -f -t "${T}.8"
tmux send-keys -t "${T}.9" "lazysar cmd" Enter
tmux select-pane -t "${T}.9"
