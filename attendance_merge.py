import csv
import argparse
import datetime
from logging import getLogger, StreamHandler, INFO, DEBUG, ERROR, WARNING
import sys
import os
import re

PRESENT = "出席"
LATE = "遅刻"
ABSENT = "欠席"

logger = getLogger(__name__)
logger.addHandler(StreamHandler(sys.stdout))
logger.setLevel(INFO)
parser = argparse.ArgumentParser()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roster_csv", help="roster.csv file path", type=str)
    parser.add_argument("timestamp_dir", help="timestamp csv directory path", type=str)
    args = parser.parse_args()
    roster_file = args.roster_csv
    timestamp_dir = args.timestamp_dir
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
    timestamp_dates = [
        date_regex.search(x).group()
        for x in os.listdir(timestamp_dir)
        if date_regex.search(x) is not None
    ]
    timestamp_dates.sort()
    # print(timestamp_dates)
    timestamp_all_data = {}  # key:date, value:timestamp_list[][]
    for td in timestamp_dates:
        with open(os.path.join(timestamp_dir, td + ".csv"), "r") as f:
            reader = csv.reader(f)
            timestamp_all_data[td] = [x for x in reader]
    result_header = ["学籍番号", "氏名", *timestamp_dates]
    result_data_all = []
    for roster_row in roster_data:
        result_data = {}
        result_data["学籍番号"] = roster_row[0]
        result_data["氏名"] = roster_row[3]

        for td, timestamps in timestamp_all_data.items():
            present = False
            late = False
            for timestamp in timestamps:
                if timestamp[1] == result_data["学籍番号"]:
                    if datetime.time(
                        *tuple([int(x) for x in timestamp[0].split(":")])
                    ) <= datetime.time(9, 25, 0):
                        present = True
                    else:
                        late = True
            if present:
                result_data[td] = PRESENT
            elif late:
                result_data[td] = LATE
            else:
                result_data[td] = ABSENT
        result_data_all.append(result_data)
    with open("attendance.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=result_header)
        writer.writeheader()
        writer.writerows(result_data_all)


if __name__ == "__main__":
    main()
