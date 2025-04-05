import argparse
import csv
import curses
import plotille
import json
import os
import re
import shutil
import subprocess

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


ANSI_TO_CURSES_COLOR_MAP = {
    0: 0,  # Default
    30: curses.COLOR_BLACK,
    31: curses.COLOR_RED,
    32: curses.COLOR_GREEN,
    33: curses.COLOR_YELLOW,
    34: curses.COLOR_BLUE,
    35: curses.COLOR_MAGENTA,
    36: curses.COLOR_CYAN,
    37: curses.COLOR_WHITE,
    90: curses.COLOR_BLACK + 8,  # Bright black
    91: curses.COLOR_RED + 8,
    92: curses.COLOR_GREEN + 8,
    93: curses.COLOR_YELLOW + 8,
    94: curses.COLOR_BLUE + 8,
    95: curses.COLOR_MAGENTA + 8,
    96: curses.COLOR_CYAN + 8,
    97: curses.COLOR_WHITE + 8,
}

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
    verbose: Optional[str] = None
    debug: Optional[bool] = False
    title: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    y_label: Optional[str] = None
    y_max: Optional[int] = None
    dev: Optional[str] = None
    iface: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    ago: Optional[str] = None
    start: str = "00:00:00"
    end: str = "23:59:59"
    refresh: Optional[int] = None
    watch: Optional[str] = None
    presets_file: Optional[str] = None
    preset: Optional[str] = None
    list_presets: bool = False
    no_legend: bool = False
    panelized: bool = False
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
            "--verbose",
            "-v",
            action="store_true",
            help="Verbose mode - used with debugging, pass method as argument",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Debug mode - do not use curses",
        )
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
            "--width",
            type=int,
            help="Width",
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
            "--refresh",
            type=int,
            help="Refresh every given number of seconds",
        )
        parser.add_argument(
            "--watch",
            help="Watch file - when it changes inode or time, exit refresh mode",
        )
        parser.add_argument(
            "--presets-file",
            help="Presets file name",
        )
        parser.add_argument(
            "--no-legend",
            action="store_true",
            help="Do not print legend",
        )
        parser.add_argument(
            "--panelized",
            action="store_true",
            help="Expect to run in panelized setup (like zellij)",
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
            debug=parsed_args.debug,
            verbose=parsed_args.verbose,
            title=parsed_args.title,
            height=parsed_args.height,
            width=parsed_args.width,
            y_label=parsed_args.y_label,
            y_max=parsed_args.y_max,
            dev=parsed_args.dev,
            iface=parsed_args.iface,
            include=parsed_args.include,
            exclude=parsed_args.exclude,
            ago=parsed_args.ago,
            start=parsed_args.start,
            end=parsed_args.end,
            refresh=parsed_args.refresh,
            watch=parsed_args.watch,
            presets_file=parsed_args.presets_file,
            preset=parsed_args.preset,
            no_legend=parsed_args.no_legend,
            panelized=parsed_args.panelized,
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
                self.args.start = (datetime.now() - timedelta(minutes=int(ago_is_time.group(1)))).strftime("%H:%M:%S")
                self.args.end = datetime.now().strftime("%H:%M:%S")
            else:
                ago_days = int(self.args.ago)
            day = (datetime.now() - timedelta(days=ago_days)).strftime("%d")
            sar_args += ["-f", f"/var/log/sysstat/sa{day}"]
        if not self.args.end:
            self.args.end = "23:59:59"

        sar_args += ["-s", self.args.start]
        sar_args += ["-e", self.args.end]

        def parse_time(time_str):
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Time data '{time_str}' does not match any supported format")

        total_seconds = (parse_time(self.args.end) - parse_time(self.args.start)).total_seconds()

        interval = int(total_seconds / self.get_chart_width() / 3)
        if interval:
            sar_args += ["-i", str(interval)]
        return sar_args

    def exec_sar(self, sar_extra_args):
        env_vars = os.environ.copy()
        env_vars["LC_ALL"] = "C"
        sar_cmd = ["sar"] + self.sar_args + sar_extra_args

        if self.args.host:
            sar_cmd = ["ssh", "-n", "-T", self.args.host] + sar_cmd

        try:
            if self.args.verbose:
                print(f"Debug: {' '.join(sar_cmd)}")
            process = subprocess.Popen(sar_cmd, stdout=subprocess.PIPE, env=env_vars)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"Error: 'sar' command failed with exit code {process.returncode}. Command was: {sar_cmd}")
                print(stderr)  # Print the error message from stderr
                exit(1)
        except FileNotFoundError:
            print("Error: 'sar' command not found. Please install sysstat package.")
            exit(1)

        return stdout.decode("utf-8").splitlines()

    def get_chart_width(self):
        columns = self.args.width or self.terminal_size.columns
        return max(5, columns - self.Y_LEGEND_WIDTH - 12)

    def get_chart_output(self, headers, times, data_columns):
        fig = plotille.Figure()
        fig.origin = False
        fig.x_label = "t"
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
        y_max = self.args.y_max if self.args.y_max else max(max(values) for values in data_columns.values())
        fig.set_y_limits(min_=0, max_=y_max)

        y_width = self.Y_LEGEND_WIDTH
        if y_max > 9999:
            y_precision = 0
        else:
            y_precision = 2

        def float_formatter(val, delta, chars=None, left=True):
            return f"{{:>{y_width}.{y_precision}f}}".format(val)

        show_legend = self.args.panelized or (len(headers) > 2 and self.terminal_size.lines >= 14)

        fig.register_label_formatter(float, float_formatter)

        fig.width = self.get_chart_width()
        fig.height = max(
            5,
            (
                self.args.height
                if self.args.height
                else self.terminal_size.lines
                - 4
                - (1 if self.args.title else 0)
                - (len(headers) + 1 if show_legend and not self.args.panelized else 1)
            ),
        )

        def custom_x_tick_formatter(val, delta):
            dt = datetime.fromtimestamp(val)
            return dt.strftime("%H:%M").center(7)

        setattr(fig, "x_ticks_fkt", custom_x_tick_formatter)

        return fig.show(legend=show_legend)

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
                if (self.args.dev and parts[1] == "DEV") or (self.args.iface and parts[1] == "IFACE"):
                    filter_value = parts[1]
            if len(parts) < 2 or parts[0] == "Average:":
                continue
            if i > 3 and parts[0] == "00:00:00":
                break
            if (
                i > 2
                and filter_value
                and (
                    (filter_value == "DEV" and self.args.dev and self.args.dev != parts[1])
                    or (filter_value == "IFACE" and self.args.iface and self.args.iface != parts[1])
                )
            ):
                continue
            filtered_lines.append("\t".join(parts))

        if self.args.debug:
            print("Filtered:")
            print("\n".join(filtered_lines))
        return filtered_lines

    def process_data(self):
        reader = csv.DictReader(self.sar_lines, delimiter="\t")

        headers = reader.fieldnames or []

        if self.include_columns and not self.exclude_columns:
            include_set = set(self.include_columns)
            self.exclude_columns = [col for col in headers[1:] if col not in include_set]

        ignore_indices = [headers.index(col) for col in self.exclude_columns if col in headers]
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

    def convert_data(self):
        [headers, times, data_columns] = self.process_data()

        if not times:
            print("Error: no data matches.")
            exit(1)

        if not data_columns:
            print("Error: no numerical data left.")
            exit(1)

        self.get_terminal_size()
        raw_output = self.get_chart_output(headers, times, data_columns)

        chart_output = []
        legend_output = []
        legend_found = False
        for line in raw_output.splitlines():
            if not len(line):
                continue
            if line.startswith("Legend:"):
                legend_found = True
            if legend_found:
                legend_output.append(f" {line} ")
            else:
                chart_output.append(line)

        self.output = "\n".join(chart_output)
        self.legend = "\n".join(legend_output[2:])

    def text_output(self):
        if self.args.title:
            print(self.args.title)
        print(self.output)
        if self.legend and not self.args.no_legend:
            print(self.legend)

    def refresh_data(self):
        oldest_time = self.sar_lines[1].split("\t", 2)[0]
        self.sar_lines = [line for line in self.sar_lines if not line.startswith(oldest_time)]
        sar_fresh_lines = self.exec_sar([f"{self.args.refresh}", "1"])
        fresh_filtered_lines = self.filter_data(sar_fresh_lines)
        self.sar_lines += fresh_filtered_lines[1:]

    def curses_init(self):
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        curses.use_default_colors()
        for ansi_code, curses_color in ANSI_TO_CURSES_COLOR_MAP.items():
            curses.init_pair(ansi_code, curses_color, -1)
        stdscr.keypad(True)
        return stdscr

    def add_curses(self, stdscr, row, col, data):
        for i, line in enumerate(data.splitlines()):
            x_pos = 0
            current_color = 0
            j = 0

            while j < len(line):
                char = line[j]
                if char == "\033":
                    ansi_code = ""
                    j += 2
                    while line[j] != "m":
                        ansi_code += line[j]
                        j += 1
                    current_color = int(ansi_code)
                    j += 1
                    continue

                stdscr.addstr(row + i, col + x_pos, char, curses.color_pair(current_color))
                x_pos += 1
                j += 1

    def get_watch_info(self):
        if self.args.watch:
            try:
                file_stat = os.stat(self.args.watch)
                return file_stat.st_ino, file_stat.st_mtime
            except Exception:  # Catch other potential errors
                pass
        return None, None

    def run(self):
        self.parser_args()
        sar_raw_lines = self.exec_sar(self.get_time_sar_args())
        self.sar_lines = self.filter_data(sar_raw_lines)
        self.output = None
        self.legend = None

        if len(self.sar_lines) == 1:
            print("Error: no data found - missing --dev or --iface?")
            exit(1)

        self.convert_data()

        [watch_inode, watch_time] = self.get_watch_info()

        if self.args.panelized:
            stdscr = self.curses_init()
            while True:
                try:
                    self.add_curses(stdscr, 0, 0, self.output)
                    self.add_curses(stdscr, 2, 14, self.legend)
                    stdscr.refresh()
                    if not self.args.refresh:
                        break

                    [new_watch_inode, new_watch_time] = self.get_watch_info()
                    if new_watch_time != watch_time or new_watch_inode != watch_inode:
                        break

                    self.refresh_data()
                    self.convert_data()
                except Exception:
                    curses.endwin()
                    stdscr = self.curses_init()
            curses.nocbreak()
            stdscr.keypad(False)
            curses.echo()
        else:
            while True:
                self.text_output()
                if not self.args.refresh:
                    break
                self.refresh_data()
                self.convert_data()


sar_chart = LazySar()
sar_chart.run()
