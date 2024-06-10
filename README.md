# lazysar

Visualize *sar/sysstats* data in multipane terminal with "zooming" possibility and multiple host support. An alternative to kSar, sarplot.

## Installation

Prerequisites:

- python3
- `apt-get install sysstat` - obvious, you probably have this already running

For panel support:
- https://zellij.dev/
```sh
curl -L https://github.com/zellij-org/zellij/releases/latest/download/zellij-x86_64-unknown-linux-musl.tar.gz | tar xvz --no-same-owner && mv -v zellij /usr/local/bin
```
- `apt-get install rlwrap` - (optional) to provide command line history

Installation:

```sh
git clone git@github.com:brablc/lazysar.git /usr/local/lib/lazysar
/usr/local/lib/lazysar/install.sh
```

## Usage

`lazysar` calls `sar` command to get data. It would pass parameters after `--` to sar. Additionally it would simplify selecting days by transforming `--ago N` to something like `-f /var/log/sysstat/sa$(date -d 'N days ago' +'%d')`. Use `--ago 0` for today.

Some charts have multiple sets of data, namely disk and network. Use `--dev=sda` or `--iface=eth1` to select the right set.

### Ad-hoc use

```sh
lazysar --ago=1 -- -i 300 -u
```

### Use presets

Presets combine multiple parameters, like excluding, including columns, describing labels, ... to make the charts more readable.

See [presets.json](./presets.json). File in `$HOME/.config/lazysar/presets.json` has precedence.

```sh
# Show one chart
lazysar --preset=cpu -- -i 300

# Show all charts
lazysar -l | xargs -I{} lazysar --dev=sda --iface=eth1 --ago=1 --preset={} --height=30 -- -i 300
```

### Use panel

Show multiple charts predefined in zellij layout format. Layout will be searched first in `$HOME/.config/zellij/layouts/` and if not found in project's `./layouts`.

```sh
lazysar panel [LAYOUT_NAME]
```

Use the bottom panel to send different set of arguments to all panes (in all sessions!) at once. Examples:

```
# today with interval 5 minutes
--dev=sda --iface=eth1 --ago=0 -- -i 300

# yesterday with interval 1 minute in the time 06:00 to 07:00 - zooming ;-)
--dev=sda --iface=eth1 --ago=1 -- -i 60 -s 06:00 -e 07:00

# loop with last 15 minutes
LOOP --dev=sda --iface=eth1 --ago=15m -- -i 5
```

#### Basic panel example:

Uses [layouts/basic.kdl](./layouts/basic.kdl) - should work out of the box.

![image](https://github.com/brablc/lazysar/assets/841734/57a5f5f1-811c-4cd8-8e9a-fa2c174b4279)

#### Multiple hosts zoomed to incident time:

Uses [layouts/hosts.kdl](./layouts/hosts.kdl) - needs to ba adapted to fix host names (assumes `node1` and `node2`).

The basic example uses `cpu` preset, while mutliple hosts uses `cpu100` so the charts are comparable.

![image](https://github.com/brablc/lazysar/assets/841734/d182e8f4-a0c7-4f1f-9a64-0e5e027f5e9f)

## Credits

Uses [Plotille](https://github.com/tammoippen/plotille) for visualization.
