import argparse
import csv
import datetime
import os
import re
import sys
import traceback
from logging import DEBUG, INFO, StreamHandler, getLogger

PRESENT = "2"
LATE = "1"
ABSENT = "0"

logger = getLogger(__name__)
logger.addHandler(StreamHandler(sys.stdout))
logger.setLevel(INFO)


def _to_time(time: str):
    splitter = time.count(":")
    logger.debug(splitter)
    if splitter == 2:
        return datetime.datetime.strptime(time, "%H:%M:%S")
    elif splitter == 1:
        return datetime.datetime.strptime(time, "%H:%M")
    else:
        raise ValueError(f"Invalid argument _to_time({time})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roster_csv", help="roster.csv file path", type=str)
    parser.add_argument("timestamp_dir", help="timestamp csv directory path", type=str)
    parser.add_argument("--debug", help="set debug mode", action="store_true")
    parser.add_argument(
        "-a",
        "--all",
        help="set mode to export all dates attendance",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--date",
        help="set output date",
        type=str,
        default=datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "-t", "--time", help="set limit time(default=9:25:00)", type=str
    )
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(DEBUG)
    roster_file = args.roster_csv
    timestamp_dir = args.timestamp_dir
    try:
        limit_time = (
            _to_time(args.time) if args.time is not None else _to_time("9:25:00")
        )
    except ValueError as e:
        if args.debug:
            logger.error(traceback.format_exc())
        else:
            logger.error(traceback.format_exception_only(type(e), e)[0].strip())
        return
    if not os.path.isfile(roster_file):
        logger.error("roster file does not exist")
        return
    if not os.path.isdir(timestamp_dir):
        logger.error("timestamp directory does not exist")
        return
    roster_data = []
    with open(roster_file, "r") as f:
        reader = csv.reader(f)
        next(reader)
        roster_data = [x for x in reader]
    if len(roster_data) == 0:
        logger.info("roster data is empty")
        return
    date_regex = re.compile("[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])")
    if args.all:
        timestamp_dates = [
            date_regex.search(x).group()
            for x in os.listdir(timestamp_dir)
            if date_regex.search(x) is not None
        ]
    else:
        if os.path.isfile(os.path.join(timestamp_dir, args.date + ".csv")):
            timestamp_dates = [args.date]
        else:
            logger.error(f"{args.date}.csv not found")
            return
    timestamp_dates.sort()
    # print(timestamp_dates)
    timestamp_all_data = {}  # key:date, value:timestamp_list[][]
    for td in timestamp_dates:
        with open(os.path.join(timestamp_dir, td + ".csv"), "r") as f:
            reader = csv.reader(f)
            timestamp_all_data[td] = [x for x in reader]
    result_header = [
        "学籍番号",
        "氏名",
        *timestamp_dates,
        *[x + "(time)" for x in timestamp_dates],
    ]
    result_data_all = []
    for roster_row in roster_data:
        result_data = {}
        result_data["学籍番号"] = roster_row[0]
        result_data["氏名"] = roster_row[3]

        for td, timestamps in timestamp_all_data.items():
            present = False
            late = False
            fastest_time: datetime.time = None
            for timestamp in timestamps:
                if timestamp[1] == result_data["学籍番号"]:
                    try:
                        ts = _to_time(timestamp[0])
                    except ValueError as e:
                        if args.debug:
                            logger.error(traceback.format_exc())
                        else:
                            logger.error(
                                traceback.format_exception_only(type(e), e)[0].strip()
                            )
                        return
                    if fastest_time is None or ts < fastest_time:
                        fastest_time = ts
                    if ts <= limit_time:
                        present = True
                    else:
                        late = True
            if present:
                result_data[td] = f"{PRESENT}"
                result_data[td + "(time)"] = fastest_time.strftime("%H:%M:%S")
            elif late:
                result_data[td] = f"{LATE}"
                result_data[td + "(time)"] = fastest_time.strftime("%H:%M:%S")
            else:
                result_data[td] = ABSENT
        result_data_all.append(result_data)
    with open("attendance.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=result_header)
        writer.writeheader()
        writer.writerows(result_data_all)
    logger.info("Process completed")


if __name__ == "__main__":
    main()
