#!/usr/bin/env bash
# swarm-nodes layout: discover Docker Swarm nodes via "docker node ls",
#                     rows = presets, columns = nodes.
#                     Local node runs without --host; remote nodes use --host (ssh).

PRESETS="${PRESETS:-cpu100 disk_bytes network_bytes}"
LOCAL_HOSTNAME=$(hostname)

# Discover swarm nodes: hostnames from "docker node ls"
mapfile -t NODES < <(docker node ls --format '{{.Hostname}}' 2>/dev/null)

if [[ ${#NODES[@]} -eq 0 ]]; then
  echo "No Docker Swarm nodes found. Is this host a swarm manager?"
  exit 1
fi

WIN="swarm-nodes"
T="${TMUX_SESSION:+${TMUX_SESSION}:}${WIN}"

read -ra PRESET_ARR <<< "$PRESETS"
NUM_ROWS=${#PRESET_ARR[@]}
NUM_COLS=${#NODES[@]}

tmux new-window ${TMUX_SESSION:+-t "$TMUX_SESSION"} -n "$WIN"

# Create rows by splitting vertically, then split each row into columns
# First, create NUM_ROWS-1 horizontal splits to make rows
for ((r = 1; r < NUM_ROWS; r++)); do
  tmux split-window -v -t "${T}.0"
done
tmux select-layout -t "$T" even-vertical

# Now split each row into columns
# After even-vertical, panes are numbered 0..NUM_ROWS-1 top to bottom
for ((r = NUM_ROWS - 1; r >= 0; r--)); do
  for ((c = 1; c < NUM_COLS; c++)); do
    tmux split-window -h -t "${T}.${r}"
  done
done
tmux select-layout -t "$T" tiled

# Assign commands: row = preset, col = node
# With tiled layout after our splits, panes are ordered left-to-right, top-to-bottom
PANE=0
for PRESET in "${PRESET_ARR[@]}"; do
  for NODE in "${NODES[@]}"; do
    if [[ "$NODE" == "$LOCAL_HOSTNAME" ]]; then
      HOST_FLAG=""
    else
      HOST_FLAG="--host $NODE"
    fi
    tmux select-pane -t "${T}.${PANE}" -T "$NODE: $PRESET"
    tmux send-keys -t "${T}.${PANE}" "lazysar client --preset $PRESET $HOST_FLAG" Enter
    ((PANE++))
  done
done

# Add command pane at the bottom — split the full window, not a single pane
LAST_PANE=$((PANE - 1))
tmux select-layout -t "$T" tiled
tmux split-window -v -l 5 -f -t "${T}.${LAST_PANE}"
tmux send-keys -t "${T}.${PANE}" "lazysar cmd" Enter
tmux select-pane -t "${T}.${PANE}"
