import argparse
import csv
import plotille
import json
import os
import re
import shutil
import subprocess
import sys

from datetime import datetime, timedelta


def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M:%S")


def extract_first_number(s):
    match = re.search(r"[-+]?\d*\.?\d+", s)
    return float(match.group()) if match else None


def float_preformatter_len(val):
    return len("{:.2f}".format(val))


colors = [
    "bright_cyan",
    "bright_yellow",
    "bright_magenta",
    "bright_green",
    "bright_blue",
    "bright_red",
    "bright_white",
]

### Parse arguments ###

parser = argparse.ArgumentParser(description="Plot SAR data")
parser.add_argument(
    "--title",
    default=None,
    help="Title of the plot",
)
parser.add_argument(
    "--height",
    type=int,
    help="Height",
)
parser.add_argument(
    "--clear",
    action="store_true",
    help="Clear screen before",
)
parser.add_argument(
    "--x-label",
    default="Time",
    help="Label for the x-axis",
)
parser.add_argument(
    "--y-label",
    default=None,
    help="Label for the y-axis",
)
parser.add_argument(
    "--y-max",
    type=int,
    default=None,
    help="Max value for y-axis",
)
parser.add_argument(
    "--dev",
    help="Filter on DEV column if present",
)
parser.add_argument(
    "--iface",
    help="Filter on IFACE column if present",
)
parser.add_argument(
    "--include",
    help="Only show some columns (by name with comma separator)",
)
parser.add_argument(
    "--exclude",
    help="Exclude some columns (by name with comma separator)",
)
parser.add_argument(
    "--ago",
    "-a",
    help="Specify the time ago for sar, without unit its days. With 15m it would become today 15 minutes ago.",
)
parser.add_argument(
    "--presets-file",
    help="Presets file name",
)
parser.add_argument(
    "--preset",
    "-p",
    help="Presets name",
)
parser.add_argument(
    "--list-presets",
    "-l",
    action="store_true",
    help="List all presets",
)
parser.add_argument(
    "--host",
    help="Execute sar over ssh",
)
parser.add_argument(
    "--",
    dest="sar_args",
    nargs=argparse.REMAINDER,
    help="Arguments for sar command",
)

args, sar_args = parser.parse_known_args()

presets_file = os.path.join(os.path.dirname(__file__), "presets.json")
if args.presets_file:
    presets_file = args.presets_file


def load_presets():
    if os.path.isfile(presets_file):
        with open(presets_file, "r") as file:
            return json.load(file)


if args.list_presets:
    presets = load_presets()
    if not presets:
        print(f"Error: presets file not found {presets_file}")
        exit(1)
    for key in presets.keys():
        print(key)
    exit()

if args.preset:
    presets = load_presets()
    if presets and args.preset in presets:
        input_string = presets[args.preset]["args"]
        pattern = r"(--\S+?='.*?'|--\S+?=\S+|--\S+|-\S\s\S)"
        matches = re.findall(pattern, input_string)
        preset_args = parser.parse_args(matches)
        for key, value in vars(preset_args).items():
            if getattr(args, key) is None and value is not None:
                if isinstance(value, str):
                    value = re.sub(r"^(['\"])(.*)\1$", r"\2", value)
                setattr(args, key, value)
        sar_args += presets[args.preset]["sar"].split(" ")
    else:
        print("Preset does not exist, use --list-presets")
        exit(1)

sar_args = [arg for arg in sar_args if arg != "--"]

exclude_columns = args.exclude.split(",") if args.exclude else []
include_columns = args.include.split(",") if args.include else []

if args.ago:
    ago_is_time = re.match(r"^(\d+)m$", args.ago, re.IGNORECASE)
    if ago_is_time:
        ago_days = 0
        sar_args += [
            "-s",
            (datetime.now() - timedelta(minutes=int(ago_is_time.group(1)))).strftime(
                "%H:%M"
            ),
        ]
    else:
        ago_days = int(args.ago)
    day = (datetime.now() - timedelta(days=ago_days)).strftime("%d")
    sar_args += ["-f", f"/var/log/sysstat/sa{day}"]

terminal_size = shutil.get_terminal_size()

### Get data

env_vars = os.environ.copy()
env_vars["LC_ALL"] = "C"
sar_cmd = ["sar"] + sar_args
if args.host:
    sar_cmd = ["ssh", "-n", "-T", args.host] + sar_cmd
try:
    process = subprocess.Popen(sar_cmd, stdout=subprocess.PIPE, env=env_vars)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error: 'sar' command failed with exit code {process.returncode}")
        print(stderr)  # Print the error message from stderr
        exit(1)
except FileNotFoundError:
    print("Error: 'sar' command not found. Please install sysstat package.")
    exit(1)

lines = stdout.decode("utf-8").splitlines()

filter_value = None

# Prepare the data according to the awk script logic
filtered_lines = []
for i, line in enumerate(lines):
    if i < 2:
        continue
    parts = line.split()
    if i == 2:
        parts[0] = "Time"
        if (args.dev and parts[1] == "DEV") or (args.iface and parts[1] == "IFACE"):
            filter_value = parts[1]
    if i > 3 and parts[0] == "00:00:00":
        break
    if parts[0] == "Average:" or len(parts) < 2:
        continue
    if (
        i > 2
        and filter_value
        and (
            (filter_value == "DEV" and args.dev and args.dev != parts[1])
            or (filter_value == "IFACE" and args.iface and args.iface != parts[1])
        )
    ):
        continue
    filtered_lines.append("\t".join(parts))

reader = csv.DictReader(filtered_lines, delimiter="\t")

headers = reader.fieldnames or []

if include_columns and not exclude_columns:
    include_set = set(include_columns)
    exclude_columns = [col for col in headers[1:] if col not in include_set]

ignore_indices = [headers.index(col) for col in exclude_columns if col in headers]
headers = [h for i, h in enumerate(headers) if i not in ignore_indices]

data_columns = {header: [] for header in headers[1:]}

non_numeric_columns = set()

times = []
for row in reader:
    times.append(parse_time(row["Time"]))
    for header in headers[1:]:
        number = extract_first_number(row[header])
        if number is not None:
            data_columns[header].append(number)
        else:
            non_numeric_columns.add(header)

# Remove columns with non-numeric values
for header in non_numeric_columns:
    if header in data_columns:
        del data_columns[header]

if not data_columns:
    print("Error: no numerical data left.")
    exit(1)

fig = plotille.Figure()
fig.origin = False
if args.x_label:
    fig.x_label = args.x_label
if args.y_label:
    fig.y_label = args.y_label
if terminal_size.columns < 64:
    fig.x_label = fig.x_label[0]

for i, (header, values) in enumerate(data_columns.items()):
    fig.plot(times, values, label=header, lc=colors[i % len(colors)])

time_diff = times[-1] - times[0]
if time_diff > timedelta(hours=23):
    start_time = times[0].replace(hour=0, minute=0, second=0)
    end_time = start_time + timedelta(hours=24)
else:
    start_time = min(times)
    end_time = max(times)

fig.set_x_limits(min_=start_time.timestamp(), max_=end_time.timestamp())
y_max = (
    args.y_max if args.y_max else max(max(values) for values in data_columns.values())
)
fig.set_y_limits(min_=0, max_=y_max)

y_width = 10
if y_max > 9999:
    y_precision = 0
else:
    y_precision = 2


def float_formatter(val, delta, chars=None, left=True):
    return f"{{:>{y_width}.{y_precision}f}}".format(val)


show_legend = len(headers) > 2 and terminal_size.lines >= 14

fig.register_label_formatter(float, float_formatter)

fig.width = max(5, terminal_size.columns - 9 - len(fig.x_label) - 3 - y_width - 2)
fig.height = max(
    5,
    (
        args.height
        if args.height
        else terminal_size.lines - 4 - (len(headers) + 3 if show_legend else 0)
    ),
)


def custom_x_tick_formatter(val, delta):
    dt = datetime.fromtimestamp(val)
    return dt.strftime("%H:%M").center(7)


setattr(fig, "x_ticks_fkt", custom_x_tick_formatter)

output = fig.show(legend=show_legend)

if args.clear:
    os.system("clear")
if args.title:
    print(args.title)

print(output)
