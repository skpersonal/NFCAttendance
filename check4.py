import csv
import datetime
import json
import os
import re
import threading
import tkinter as tk
import traceback
from tkinter import *
from tkinter import filedialog, scrolledtext, ttk
import dotenv
import nfc
import simpleaudio

dotenv.load_dotenv()
SYSTEM_CODE = int(os.environ.get("SYSTEM_CODE"), 0)
SERVICE_CODE = int(os.environ.get("SERVICE_CODE"), 0)
SE_SUCCESS_AUDIO = simpleaudio.WaveObject.from_wave_file("se_success.wav")
SE_FAIL_AUDIO = simpleaudio.WaveObject.from_wave_file("se_fail.wav")


class MainWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack()
        self.settings = {}
        self.roster_list = []
        self.available_timestamps = []
        self.selected_timestamp = StringVar(master, "")
        self.timestamp_list = []
        self.roster_path = StringVar(master, "")
        self.name_list = StringVar(master)
        self.date = datetime.datetime.now(datetime.timezone(
            datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
        os.chdir(os.path.dirname(__file__))
        if not os.path.isdir("attendance"):
            os.makedirs("attendance")
        self.load_config()
        master.title("打刻ツール")
        title_label = Label(master, text="打刻ツール", font=("", 40))
        title_label.pack()
        button_frame = Frame(master)
        chk_in_button = Button(button_frame, text="出席チェック",
                               font=("", 20), command=self.show_chk_in)
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
        self.startNFC()

    def load_config(self):
        if os.path.isfile("settings.json"):
            with open("settings.json") as f:
                self.settings = json.load(f)
        self.roster_path.set(self.settings.get("roster", ""))

    def show_chk_in(self):
        self.available_timestamps = [x for x in os.listdir("attendance") if os.path.isfile(
            os.path.join("attendance", x)) and re.match("^[0-9]+\-[0-9]+\-[0-9]+\.csv$", x) is not None]
        self.available_timestamps.sort()
        new_window = tk.Toplevel(self)
        # new_window.grab_set()
        new_window.focus_set()
        options_frame = Frame(new_window)
        main_frame = Frame(new_window)

        side_frame = Frame(main_frame)
        list_frame = Frame(side_frame)
        button_frame = Frame(side_frame)
        scroll_list = Scrollbar(list_frame)
        if os.path.isfile(self.roster_path.get()):
            with open(self.roster_path.get(), "r") as f:
                reader = csv.reader(f)
                reader.__next__()
                self.roster_list = [x for x in reader]
        if os.path.isfile(self.selected_timestamp.get()):
            with open(self.selected_timestamp.get(), "r") as f:
                reader = csv.reader(f)
                self.timestamp_list = [x for x in reader]
        self.name_list.set(value=[x[3] for x in self.roster_list])

        lb = Listbox(list_frame, listvariable=self.name_list, selectmode="single",
                     yscrollcommand=scroll_list.set, height=15, width=20)
        scroll_list["command"] = lb.yview

        detail_frame = Frame(main_frame)
        detail_box = scrolledtext.ScrolledText(detail_frame, width=50)
        detail_box.configure(state=DISABLED)
        detail_box.pack()
        detail_frame.grid(row=0, column=1)

        def show_details(e):
            detail_box.configure(state=NORMAL)
            detail_box.delete("1.0", END)
            selected_student_name = lb.get(lb.curselection())
            lb.selection_clear(0, END)
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

        lb.bind("<<ListboxSelect>>", show_details)
        lb.grid(row=0, column=0)
        scroll_list.grid(row=0, column=1, sticky=N+S)

        def update_data():
            if len(self.roster_list) == 0:
                return
            if len(self.timestamp_list) == 0:
                return
            for i, name in enumerate(lb.get(0, END)):
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
                out_log = [
                    x for x in st_log if str(x[2]) == "OUT"]
                lb.itemconfigure(i, background="")
                if len(in_log) == 0:
                    lb.itemconfigure(i, background="pink")
                if len(in_log) > 0:
                    # ここで遅刻判定用の時刻を設定する(デフォルトは9:25:00)
                    if datetime.time(*tuple([int(x) for x in in_log[0][0].split(":")])) > datetime.time(9, 25, 0):
                        lb.itemconfigure(i, background="yellow")

        def timestamp_load(e):
            timestamp_selector.selection_clear()
            if os.path.isfile(os.path.join("attendance", self.selected_timestamp.get())):
                with open(os.path.join("attendance", self.selected_timestamp.get()), "r") as f:
                    reader = csv.reader(f)
                    self.timestamp_list = [x for x in reader]
            update_data()

        timestamp_selector = ttk.Combobox(
            options_frame, textvariable=self.selected_timestamp, values=self.available_timestamps, exportselection=False, width=12, state='readonly')
        if len(self.available_timestamps) > 0:
            timestamp_selector.set(
                self.available_timestamps[-1])
            timestamp_load(None)
        timestamp_selector.bind("<<ComboboxSelected>>", timestamp_load)
        timestamp_selector.grid(row=0, column=0)

        def set_roster_path():
            self.roster_path.set(filedialog.askopenfilename(
                filetypes=[("csv", "*.csv")], initialdir=self.roster_path.get()))
            if os.path.isfile(self.roster_path.get()):
                self.settings["roster"] = self.roster_path.get()
                with open("settings.json", "w") as f:
                    json.dump(self.settings, f)
                with open(self.roster_path.get(), "r") as f:
                    reader = csv.reader(f)
                    reader.__next__()
                    self.roster_list = [x for x in reader]
            self.name_list.set([x[3] for x in self.roster_list])
            update_data()

        ref_text = Entry(
            options_frame, textvariable=self.roster_path, width=40)
        ref_text.grid(row=0, column=1)
        ref_button = Button(options_frame, text="参照",
                            command=set_roster_path)
        ref_button.grid(row=0, column=2)

        update_button = Button(button_frame, text="更新",
                               command=update_data)
        update_button.pack()
        list_frame.pack(fill='y')
        button_frame.pack()
        side_frame.grid(row=0, column=0, sticky=N+S)
        options_frame.pack()
        main_frame.pack()
        update_data()

    def stop(self):
        self.loop = False

    def startNFC(self):
        print("startNFC")
        try:
            clf = nfc.ContactlessFrontend("usb")
            self.loop = True
            t = threading.Thread(target=self.get_connect,
                                 args=(clf,), daemon=True)
            t.start()
            print("NFC thread started")
            print("NFC ready")
            self.printv("準備完了")
        except OSError as e:
            if e.errno == 19:
                print("NFCカードリーダーが検出できません")
                self.printv("NFCカードリーダーが検出できません\nカードリーダーを接続してから開き直してください")
            else:
                print(traceback.format_exc())
            self.stop()
        except Exception:
            self.stop()

    def printv(self, text):
        # for s in reversed(text.split("\n")):
        self.timeline_lb.configure(state=NORMAL)
        self.timeline_lb.insert(tk.END, text+"\n")
        self.timeline_lb.configure(state=DISABLED)

    def on_connect(self, tag):
        try:
            idm, ppm = tag.polling()
            if (tag.sys != SYSTEM_CODE):
                print("This card is not a student card (sys: "+hex(tag.sys)+")")
                return True
            tag.idm, tag.ppm, tag.sys = idm, ppm, SYSTEM_CODE

            if isinstance(tag, nfc.tag.tt3.Type3Tag):
                try:
                    sc = nfc.tag.tt3.ServiceCode(
                        SERVICE_CODE >> 6, SERVICE_CODE & 0x3f)
                    bc = nfc.tag.tt3.BlockCode(1, service=0)
                    card_data = tag.read_without_encryption([sc], [bc])
                    s_num = bytearray.decode(card_data[0:8])
                    output = ""
                    if self.mode.get() == 0:
                        output = (datetime.datetime.now(datetime.timezone(
                            datetime.timedelta(hours=9))).strftime("%H:%M:%S"), s_num, "IN")
                    elif self.mode.get() == 1:
                        output = (datetime.datetime.now(datetime.timezone(
                            datetime.timedelta(hours=9))).strftime("%H:%M:%S"), s_num, "OUT")
                    with open(os.path.join("attendance", self.date+".csv"), "a") as f:
                        writer = csv.writer(f)
                        writer.writerow([*output])
                    print(*output)
                    self.printv(" ".join(output))
                    SE_SUCCESS_AUDIO.play()
                except Exception as e:
                    print(traceback.format_exc())
            else:
                print('error: invalid card')
        except Exception as e:
            print(traceback.format_exc())
        return True

    def get_connect(self, clf: nfc.ContactlessFrontend):
        print("get_connect")
        try:
            while self.loop:
                clf.connect(
                    rdwr={'on-connect': self.on_connect})
        finally:
            clf.close()
            print("clf closed")


def main():
    window = tk.Tk()
    main_window = MainWindow(window)
    main_window.mainloop()


if __name__ == "__main__":
    main()
