import argparse
import csv
import datetime
import os
import re
import sys
import threading
import traceback
from logging import DEBUG, INFO, StreamHandler, getLogger

import dotenv
import nfc
import simpleaudio

ATTENDANCE_FOLDER_PATH = "attendance"

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


# noinspection DuplicatedCode
class Main:
    def __init__(self):
        self.loop = False
        self.settings = {}
        self.date = datetime.datetime.now(JST).strftime("%Y-%m-%d")
        os.chdir(os.path.dirname(__file__))
        if not os.path.isdir(ATTENDANCE_FOLDER_PATH):
            os.makedirs(ATTENDANCE_FOLDER_PATH)
        # edit after
        self.mode = 0  # 0=IN, 1=OUT
        self.start_nfc()

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
        except OSError as e:
            if e.errno == 19:
                logger.debug("NFCカードリーダーが検出できません")
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
                if self.mode == 0:
                    output = (datetime.datetime.now(JST).strftime("%H:%M:%S"), s_num, "IN")
                elif self.mode == 1:
                    output = (datetime.datetime.now(JST).strftime("%H:%M:%S"), s_num, "OUT")
                with open(os.path.join(ATTENDANCE_FOLDER_PATH,
                                       self.date + ".csv"), "a") as f:
                    writer = csv.writer(f)
                    writer.writerow([*output])
                logger.info(" ".join(output))
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
    m = Main()
    while True:
        if m.mode == 0:
            mode = "出席"
        elif m.mode == 1:
            mode = "退室"
        else:
            mode = "不明"
        print("現在のモードは" + mode + "です")
        print("モードを選択してください(0=出席, 1=退室, q=終了)")
        x = input(">")
        if x == "":
            continue
        if x.lower() == "q":
            break
        if re.match("^[01]$", x):
            m.mode = int(x)
        else:
            print("そのモードはありません")


if __name__ == "__main__":
    main()
