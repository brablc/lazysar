import argparse
import csv
import plotille
import json
import os
import re
import shutil
import subprocess
import time

from dataclasses import dataclass, field
from typing import List, Optional
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


@dataclass
class Args:
    title: Optional[str] = None
    height: Optional[int] = None
    clear: bool = False
    x_label: str = "Time"
    y_label: Optional[str] = None
    y_max: Optional[int] = None
    cpu: Optional[str] = None
    dev: Optional[str] = None
    iface: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    ago: Optional[str] = None
    start: str = "00:00:00"
    end: str = "23:59:59"
    loop: Optional[int] = None
    presets_file: Optional[str] = None
    preset: Optional[str] = None
    list_presets: bool = False
    host: Optional[str] = None
    sar_args: List[str] = field(default_factory=list)


class LazySar:
    Y_LEGEND_WIDTH = 10
    sar_args = []
    exclude_columns = []
    include_columns = []

    def __init__(self) -> None:
        self.get_terminal_size()

    def get_terminal_size(self):
        self.terminal_size = shutil.get_terminal_size()

    def parser_args(self):
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
            "--cpu",
            help="Filter on CPU column if present",
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
            "--start",
            "-s",
            default="00:00:00",
            help="Start time HH:MM",
        )
        parser.add_argument(
            "--end",
            "-e",
            default="23:59:59",
            help="End time HH:MM",
        )
        parser.add_argument(
            "--loop",
            type=int,
            help="Run in a loop with given time interval in seconds",
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

        parsed_args, self.sar_args = parser.parse_known_args()

        self.args = Args(
            title=parsed_args.title,
            height=parsed_args.height,
            clear=parsed_args.clear,
            x_label=parsed_args.x_label,
            y_label=parsed_args.y_label,
            y_max=parsed_args.y_max,
            cpu=parsed_args.cpu,
            dev=parsed_args.dev,
            iface=parsed_args.iface,
            include=parsed_args.include,
            exclude=parsed_args.exclude,
            ago=parsed_args.ago,
            start=parsed_args.start,
            end=parsed_args.end,
            loop=parsed_args.loop,
            presets_file=parsed_args.presets_file,
            preset=parsed_args.preset,
            list_presets=parsed_args.list_presets,
            host=parsed_args.host,
            sar_args=parsed_args.sar_args,
        )

        presets_file = os.path.join(os.path.dirname(__file__), "presets.json")
        if self.args.presets_file:
            presets_file = self.args.presets_file

        def load_presets():
            if os.path.isfile(presets_file):
                with open(presets_file, "r") as file:
                    return json.load(file)

        if self.args.list_presets:
            presets = load_presets()
            if not presets:
                print(f"Error: presets file not found {presets_file}")
                exit(1)
            for key in presets.keys():
                print(key)
            exit()

        if self.args.preset:
            presets = load_presets()
            if presets and self.args.preset in presets:
                input_string = presets[self.args.preset]["args"]
                pattern = r"(--\S+?='.*?'|--\S+?=\S+|--\S+|-\S\s\S)"
                matches = re.findall(pattern, input_string)
                preset_args = parser.parse_args(matches)
                for key, value in vars(preset_args).items():
                    if getattr(self.args, key) is None and value is not None:
                        if isinstance(value, str):
                            value = re.sub(r"^(['\"])(.*)\1$", r"\2", value)
                        setattr(self.args, key, value)
                self.sar_args += presets[self.args.preset]["sar"].split(" ")
            else:
                print("Preset does not exist, use --list-presets")
                exit(1)

        self.sar_args = [arg for arg in self.sar_args if arg != "--"]

        self.exclude_columns = self.args.exclude.split(",") if self.args.exclude else []
        self.include_columns = self.args.include.split(",") if self.args.include else []

    def get_time_sar_args(self):
        sar_args = []
        if self.args.ago:
            ago_is_time = re.match(r"^(\d+)m$", self.args.ago, re.IGNORECASE)
            if ago_is_time:
                ago_days = 0
                self.args.start = (
                    datetime.now() - timedelta(minutes=int(ago_is_time.group(1)))
                ).strftime("%H:%M:%S")
                self.args.end = datetime.now().strftime("%H:%M:%S")
            else:
                ago_days = int(self.args.ago)
            day = (datetime.now() - timedelta(days=ago_days)).strftime("%d")
            sar_args += ["-f", f"/var/log/sysstat/sa{day}"]
        if not self.args.end:
            self.args.end = "23:59:59"

        sar_args += ["-s", self.args.start]
        sar_args += ["-e", self.args.end]

        total_seconds = (
            datetime.strptime(self.args.end, "%H:%M:%S")
            - datetime.strptime(self.args.start, "%H:%M:%S")
        ).total_seconds()

        interval = int(total_seconds / self.get_chart_width() / 3)
        if interval:
            sar_args += ["-i", str(interval)]
        return sar_args

    def exec_sar(self, time_sar_args):
        env_vars = os.environ.copy()
        env_vars["LC_ALL"] = "C"
        sar_cmd = ["sar"] + self.sar_args + time_sar_args
        if self.args.host:
            sar_cmd = ["ssh", "-n", "-T", self.args.host] + sar_cmd
        try:
            process = subprocess.Popen(sar_cmd, stdout=subprocess.PIPE, env=env_vars)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(
                    f"Error: 'sar' command failed with exit code {process.returncode}. Command was: {sar_cmd}"
                )
                print(stderr)  # Print the error message from stderr
                exit(1)
        except FileNotFoundError:
            print("Error: 'sar' command not found. Please install sysstat package.")
            exit(1)

        return stdout.decode("utf-8").splitlines()

    def filter_data(self, lines):
        filter_value = None

        # Prepare the data according to the awk script logic
        filtered_lines = []
        for i, line in enumerate(lines):
            if i < 2:
                continue
            parts = line.split()
            if i == 2:
                parts[0] = "Time"
                if (
                    (self.args.cpu and parts[1] == "CPU")
                    or (self.args.dev and parts[1] == "DEV")
                    or (self.args.iface and parts[1] == "IFACE")
                ):
                    filter_value = parts[1]
            if i > 3 and parts[0] == "00:00:00":
                break
            if parts[0] == "Average:" or len(parts) < 2:
                continue
            if (
                i > 2
                and filter_value
                and (
                    (
                        filter_value == "CPU"
                        and self.args.cpu
                        and self.args.cpu != parts[1]
                    )
                    or (
                        filter_value == "DEV"
                        and self.args.dev
                        and self.args.dev != parts[1]
                    )
                    or (
                        filter_value == "IFACE"
                        and self.args.iface
                        and self.args.iface != parts[1]
                    )
                )
            ):
                continue
            filtered_lines.append("\t".join(parts))

        return filtered_lines

    def process_data(self, lines):
        reader = csv.DictReader(lines, delimiter="\t")

        headers = reader.fieldnames or []

        if self.include_columns and not self.exclude_columns:
            include_set = set(self.include_columns)
            self.exclude_columns = [
                col for col in headers[1:] if col not in include_set
            ]

        ignore_indices = [
            headers.index(col) for col in self.exclude_columns if col in headers
        ]
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

        return [headers, times, data_columns]

    def get_x_label(self):
        label = self.args.x_label
        if self.terminal_size.columns < 64:
            label = label[0]
        return label

    def get_chart_width(self):
        return max(
            5,
            self.terminal_size.columns
            - 9
            - len(self.get_x_label())
            - 3
            - self.Y_LEGEND_WIDTH
            - 2,
        )

    def get_chart_output(self, headers, times, data_columns):
        fig = plotille.Figure()
        fig.origin = False
        fig.x_label = self.get_x_label()
        if self.args.y_label:
            fig.y_label = self.args.y_label

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
            self.args.y_max
            if self.args.y_max
            else max(max(values) for values in data_columns.values())
        )
        fig.set_y_limits(min_=0, max_=y_max)

        y_width = self.Y_LEGEND_WIDTH
        if y_max > 9999:
            y_precision = 0
        else:
            y_precision = 2

        def float_formatter(val, delta, chars=None, left=True):
            return f"{{:>{y_width}.{y_precision}f}}".format(val)

        show_legend = len(headers) > 2 and self.terminal_size.lines >= 14

        fig.register_label_formatter(float, float_formatter)

        fig.width = self.get_chart_width()
        fig.height = max(
            5,
            (
                self.args.height
                if self.args.height
                else self.terminal_size.lines
                - 4
                - (len(headers) + 3 if show_legend else 0)
            ),
        )

        def custom_x_tick_formatter(val, delta):
            dt = datetime.fromtimestamp(val)
            return dt.strftime("%H:%M").center(7)

        setattr(fig, "x_ticks_fkt", custom_x_tick_formatter)

        return fig.show(legend=show_legend)

    def run(self):
        self.parser_args()

        def run_internal():
            self.get_terminal_size()
            time_sar_args = self.get_time_sar_args()

            lines = self.exec_sar(time_sar_args)

            filtered_lines = self.filter_data(lines)
            [headers, times, data_columns] = self.process_data(filtered_lines)

            if not times:
                print("Error: no data matches.")
                exit(1)

            if not data_columns:
                print("Error: no numerical data left.")
                exit(1)

            output = self.get_chart_output(headers, times, data_columns)

            if self.args.clear:
                os.system("clear")
            if self.args.title:
                print(self.args.title)

            print(output)

        if self.args.loop:
            while True:
                run_internal()
                time.sleep(self.args.loop)

        else:
            run_internal()


sar_chart = LazySar()
sar_chart.run()
