# lazysar

Visualize *sar/sysstats* data in multipane teminal with zooming possibility. An alternative to kSar, sarplot.

## Installation

Prerequisites:

- python3
- https://zellij.dev/
- `apt-get isnstall sysstat`

Installation:

```sh
git clone git@github.com:brablc/lazysar.git /usr/local/lib/
/usr/local/lib/lazysar/install.sh
```

## Usage

`lazysar` calls `sar` command to get data. It would pass parameters after `--` to sar. Additionally it would simplify selecting days by transforming `--ago N` to something like `-f /var/log/sysstat/sa$(date -d 'N days ago' +'%d')`.

Some charts have multiple sets of data, namely disk and network. Use `--dev=sda` or `--iface=eth1` to select the right set.

```sh
lazysar --ago=1 -- -i 300 -u

# show all preset charts for yesterday,
# please change --dev and --iface to match your system
lazysar -l | xargs -I{} lazysar --dev=sda --iface=eth1 --ago=1 --preset={} --height=30 -- -i 3600
```

## Coming soon

A layout for `zellij` to show charts in panes with possibility to change the date or time.

## Credits

Uses [Plotille](https://github.com/tammoippen/plotille) for visualization.
