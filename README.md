# lazysar

Visualize *sar/sysstats* data in multipane teminal with "zooming" possibility. An alternative to kSar, sarplot.

## Installation

Prerequisites:

- python3
- https://zellij.dev/
- `apt-get install sysstat` - obvious, you probably have this already running
- `apt-get install rlwrap` - to provide command line history

Installation:

```sh
git clone git@github.com:brablc/lazysar.git /usr/local/lib/
/usr/local/lib/lazysar/install.sh
```

## Usage

`lazysar` calls `sar` command to get data. It would pass parameters after `--` to sar. Additionally it would simplify selecting days by transforming `--ago N` to something like `-f /var/log/sysstat/sa$(date -d 'N days ago' +'%d')`.

Some charts have multiple sets of data, namely disk and network. Use `--dev=sda` or `--iface=eth1` to select the right set.

### Ad-hoc use

```sh
lazysar --ago=1 -- -i 300 -u
```

### Use presets

Presets combine multiple parameters, like excluding, including columns, describing labels, ... to make the charts more readable.

See (presets.json)[./presets.json]. File in `$HOME/.config/lazysar/presets.json` has precedence.

```sh
# Show one chart
lazysar --preset=cpu -- -i 300

# Show all charts
lazysar -l | xargs -I{} lazysar --dev=sda --iface=eth1 --ago=1 --preset={} --height=30 -- -i 300
```

### Use panel

Show multiple charts predefined in (layouts/basic.kdl)[./layouts/basic.kdl] (`zellij` layout file). Layout will be searched first in `$HOME/.config/zellij/layouts/`.

```sh
lazysar panel [LAYOUT_NAME]
```
![image](https://github.com/brablc/lazysar/assets/841734/789a7a61-3b59-467e-af40-029cf8b92a70)

Use the bottom panel to send different set of parameters to all panes at once. Examples:

```
# today with interval 5 minutes
--dev=sda --iface=eth1 --ago=0 -- -i 300

# yesterday with interval 1 minute in the time 06:00 to 07:00 - zooming ;-)
--dev=sda --iface=eth1 --ago=1 -- -i 60 -s 06:00 -e 07:00
```

## Credits

Uses [Plotille](https://github.com/tammoippen/plotille) for visualization.
