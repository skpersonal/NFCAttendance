import argparse
import csv
import datetime
import json
import os
import re
import sys
import threading
import tkinter as tk
import traceback
from logging import DEBUG, INFO, StreamHandler, getLogger
from tkinter import (Button, DISABLED, END, Entry, Frame, LEFT, Label, Listbox, N, NORMAL, Radiobutton, S, Scrollbar,
                     StringVar, filedialog, scrolledtext, ttk)

import dotenv
import nfc
import simpleaudio

ATTENDANCE_FOLDER_PATH = "attendance"
SETTINGS_FILE_PATH = "settings.json"

logger = getLogger(__name__)
logger.addHandler(StreamHandler(sys.stdout))
parser = argparse.ArgumentParser()
parser.add_argument("--system", help="set SYSTEM_CODE", type=str)
parser.add_argument("--service", help="set SERVICE_CODE", type=str)
parser.add_argument("--debug", help="DEBUG mode", action="store_true")
args = parser.parse_args()
if args.debug:
    logger.setLevel(DEBUG)
else:
    logger.setLevel(INFO)
dotenv.load_dotenv()
try:
    SYSTEM_CODE = int(os.getenv("SYSTEM_CODE", "0x0001"), 0) if args.system is None \
        else int(args.system, 0)
    SERVICE_CODE = int(os.getenv("SERVICE_CODE", "0x0001"), 0) if args.service is None \
        else int(args.service, 0)
except ValueError:
    logger.error("Invalid arguments")
    exit(1)
SE_SUCCESS_AUDIO = simpleaudio.WaveObject.from_wave_file("se_success.wav")
SE_FAIL_AUDIO = simpleaudio.WaveObject.from_wave_file("se_fail.wav")
JST = datetime.timezone(datetime.timedelta(hours=9))


class MainWindow(tk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.pack()
        self.loop = False
        self.settings = {}
        self.roster_list = []
        self.available_timestamps = []
        self.selected_timestamp = StringVar(master, "")
        self.timestamp_list = []
        self.roster_path = StringVar(master, "")
        self.student_name_list = StringVar(master)
        self.date = datetime.datetime.now(JST).strftime("%Y-%m-%d")
        os.chdir(os.path.dirname(__file__))
        if not os.path.isdir(ATTENDANCE_FOLDER_PATH):
            os.makedirs(ATTENDANCE_FOLDER_PATH)
        self.load_config()
        master.title("打刻ツール")
        title_label = Label(master, text="打刻ツール", font=("", 40))
        title_label.pack()
        button_frame = Frame(master)
        chk_in_button = Button(button_frame, text="出席チェック",
                               font=("", 20), command=self.show_checker)
        chk_in_button.pack(side=LEFT)
        button_frame.pack()
        mode_label = Label(master, text="モードを選択してください", font=("", 15))
        mode_label.pack()
        self.mode = tk.IntVar(value=0)  # 0=IN, 1=OUT, 9=TEST
        rb_in = Radiobutton(master, text="出席", variable=self.mode, value=0)
        rb_out = Radiobutton(master, text="退席", variable=self.mode, value=1)
        rb_in.pack()
        rb_out.pack()
        self.timeline_lb = scrolledtext.ScrolledText(master, state=DISABLED)
        self.timeline_lb.pack()
        self.start_nfc()

    def load_config(self):
        if os.path.isfile(SETTINGS_FILE_PATH):
            with open(SETTINGS_FILE_PATH) as f:
                self.settings = json.load(f)
        self.roster_path.set(self.settings.get("roster", ""))

    def show_checker(self):
        self.available_timestamps = [x for x in os.listdir(ATTENDANCE_FOLDER_PATH)
                                     if os.path.isfile(os.path.join(ATTENDANCE_FOLDER_PATH, x))
                                     and re.match("^[0-9]+-[0-9]+-[0-9]+\.csv$", x) is not None]
        self.available_timestamps.sort()
        checker_window = tk.Toplevel(self)
        # checker_window.grab_set()
        checker_window.focus_set()
        options_frame = Frame(checker_window)
        main_frame = Frame(checker_window)

        side_frame = Frame(main_frame)
        student_list_frame = Frame(side_frame)
        update_button_frame = Frame(side_frame)
        member_scroll = Scrollbar(student_list_frame)
        if os.path.isfile(self.roster_path.get()):
            with open(self.roster_path.get(), "r") as f:
                reader = csv.reader(f)
                reader.__next__()
                self.roster_list = [x for x in reader]
        if os.path.isfile(self.selected_timestamp.get()):
            with open(self.selected_timestamp.get(), "r") as f:
                reader = csv.reader(f)
                self.timestamp_list = [x for x in reader]
        # noinspection PyTypeChecker
        self.student_name_list.set(value=[x[3] for x in self.roster_list])

        member_list = Listbox(student_list_frame, listvariable=self.student_name_list, selectmode="single",
                              yscrollcommand=member_scroll.set, height=15, width=20)
        member_scroll["command"] = member_list.yview

        detail_frame = Frame(main_frame)
        detail_box = scrolledtext.ScrolledText(detail_frame, width=50)
        detail_box.configure(state=DISABLED)
        detail_box.pack()
        detail_frame.grid(row=0, column=1)

        def _update_details(e=None):
            detail_box.configure(state=NORMAL)
            detail_box.delete("1.0", END)
            selected_student_name = member_list.get(member_list.curselection())
            member_list.selection_clear(0, END)
            st_num = None
            for x in self.roster_list:
                if x[3] == selected_student_name:
                    st_num = x[0]
                    break
            st_log = [x for x in self.timestamp_list if str(
                x[1]) == str(st_num)]
            data = "\n".join([" ".join(x) for x in st_log])
            detail_box.insert(END, data)
            detail_box.configure(state=DISABLED)

        member_list.bind("<<ListboxSelect>>", _update_details)
        member_list.grid(row=0, column=0)
        member_scroll.grid(row=0, column=1, sticky=N + S)

        def _update_student_list_color():
            if len(self.roster_list) == 0:
                return
            if len(self.timestamp_list) == 0:
                return
            for i, name in enumerate(member_list.get(0, END)):
                st_num = None
                for x in self.roster_list:
                    if x[3] == name:
                        st_num = x[0]
                        break
                if st_num is None:
                    continue
                st_log = [x for x in self.timestamp_list if str(
                    x[1]) == str(st_num)]
                in_log = [x for x in st_log if str(x[2]) == "IN"]
                # out_log = [x for x in st_log if str(x[2]) == "OUT"]
                member_list.itemconfigure(i, background="")
                if len(in_log) == 0:
                    member_list.itemconfigure(i, background="pink")
                if len(in_log) > 0:
                    # ここで遅刻判定用の時刻を設定する(デフォルトは9:25:00)
                    if (datetime.time(*tuple([int(x) for x in in_log[0][0].split(":")]))
                            > datetime.time(9, 25, 0)):
                        member_list.itemconfigure(i, background="yellow")

        def _load_timestamp(e=None):
            timestamp_selector.selection_clear()
            if os.path.isfile(os.path.join(ATTENDANCE_FOLDER_PATH, self.selected_timestamp.get())):
                with open(os.path.join(ATTENDANCE_FOLDER_PATH, self.selected_timestamp.get()), "r") as g:
                    r = csv.reader(g)
                    self.timestamp_list = [x for x in r]
            _update_student_list_color()

        timestamp_selector = ttk.Combobox(
            options_frame, textvariable=self.selected_timestamp, values=self.available_timestamps,
            exportselection=False, width=12, state='readonly')
        if len(self.available_timestamps) > 0:
            timestamp_selector.set(
                self.available_timestamps[-1])
            _load_timestamp(None)
        timestamp_selector.bind("<<ComboboxSelected>>", _load_timestamp)
        timestamp_selector.grid(row=0, column=0)

        def _set_roster_path():
            self.roster_path.set(filedialog.askopenfilename(
                filetypes=[("csv", "*.csv")], initialdir=self.roster_path.get()))
            if os.path.isfile(self.roster_path.get()):
                self.settings["roster"] = self.roster_path.get()
                with open("settings.json", "w") as g:
                    json.dump(self.settings, g)
                with open(self.roster_path.get(), "r") as g:
                    r = csv.reader(g)
                    r.__next__()
                    self.roster_list = [x for x in r]
            # noinspection PyTypeChecker
            self.student_name_list.set([x[3] for x in self.roster_list])
            _update_student_list_color()

        roster_ref_text = Entry(
            options_frame, textvariable=self.roster_path, width=40)
        roster_ref_text.grid(row=0, column=1)
        roster_ref_button = Button(options_frame, text="参照",
                                   command=_set_roster_path)
        roster_ref_button.grid(row=0, column=2)

        update_button = Button(update_button_frame, text="更新",command=_load_timestamp)
        update_button.pack()
        student_list_frame.pack(fill='y')
        update_button_frame.pack()
        side_frame.grid(row=0, column=0, sticky=N + S)
        options_frame.pack()
        main_frame.pack()
        _update_student_list_color()

    def printVal(self, text):
        self.timeline_lb.configure(state=NORMAL)
        self.timeline_lb.insert(tk.END, text + "\n")
        self.timeline_lb.configure(state=DISABLED)

    def stop_nfc(self):
        self.loop = False

    def start_nfc(self):
        logger.debug("start NFC")
        try:
            clf = nfc.ContactlessFrontend("usb")
            self.loop = True
            t = threading.Thread(target=self.get_connect,
                                 args=(clf,), daemon=True)
            t.start()
            logger.debug("NFC thread started")
            logger.debug("NFC ready")
            self.printVal("準備完了")
        except OSError as e:
            if e.errno == 19:
                logger.debug("NFCカードリーダーが検出できません")
                self.printVal("NFCカードリーダーが検出できません\nカードリーダーを接続してから開き直してください")
            else:
                logger.error(traceback.format_exc())
            self.stop_nfc()

    def on_connect(self, tag):
        try:
            if isinstance(tag, nfc.tag.tt3_sony.FelicaStandard):
                idm, ppm = tag.polling()
                if tag.sys != SYSTEM_CODE:
                    logger.debug(
                        f"This card is not a student card (sys:{hex(tag.sys)})")
                    return True
                tag.idm, tag.ppm, tag.sys = idm, ppm, SYSTEM_CODE

                sc = nfc.tag.tt3.ServiceCode(SERVICE_CODE >> 6, SERVICE_CODE & 0x3f)
                bc = nfc.tag.tt3.BlockCode(1, service=0)
                card_data = tag.read_without_encryption([sc], [bc])
                # 学籍番号のデコード
                s_num = bytearray.decode(card_data[0:8])
                output = ""
                if self.mode.get() == 0:
                    output = (datetime.datetime.now(JST).strftime("%H:%M:%S"), s_num, "IN")
                elif self.mode.get() == 1:
                    output = (datetime.datetime.now(JST).strftime("%H:%M:%S"), s_num, "OUT")
                with open(os.path.join(ATTENDANCE_FOLDER_PATH,
                                       self.date + ".csv"), "a") as f:
                    writer = csv.writer(f)
                    writer.writerow([*output])
                logger.debug(" ".join(output))
                self.printVal(" ".join(output))
                SE_SUCCESS_AUDIO.play()
            else:
                logger.debug('error: invalid card')
        except nfc.tag.TagCommandError:
            logger.error(traceback.format_exc())
        return True

    def get_connect(self, clf: nfc.ContactlessFrontend):
        logger.debug("get_connect")
        try:
            while self.loop:
                clf.connect(
                    rdwr={'on-connect': self.on_connect},
                    terminate=lambda: not self.loop
                )
        finally:
            clf.close()
            logger.debug("clf closed")


def main():
    logger.debug(f"SYSTEM_CODE={hex(SYSTEM_CODE)}")
    logger.debug(f"SERVICE_CODE={hex(SERVICE_CODE)}")
    window = tk.Tk()
    main_window = MainWindow(window)
    main_window.mainloop()


if __name__ == "__main__":
    main()
