import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo
import requests

# ==============================================================================
# 📚 BOT THỜI KHÓA BIỂU & HỌC TẬP 8A12 - VERSION 17.2 CLEAN
# 👨‍💻 Code được phát triển bởi Nguyễn Hữu Nghĩa
# ==============================================================================

DEV_NAME = "Nguyễn Hữu Nghĩa"
BOT_VERSION = "v17.2 Clean TKB"

BOT_TOKEN = "503229070296512217:duDcitgmJAlRYXbFqfikThjeaPetrKmrbPUyyfZweCmSwlvFUjdkovVfmEixbEnS"
ZALO_API_BASE = f"https://bot-api.zapps.me/bot{BOT_TOKEN}"

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DB_FILE = "school_schedule_v17.db"

http_session = requests.Session()

# Dữ liệu thời khóa biểu mẫu lớp 8A12
DEFAULT_TKB_8A12 = [
    ("T2", "07:30", "HĐTN", "Phòng 8A12"),
    ("T2", "08:15", "LS&DL(Đ)", "Phòng 8A12"),
    ("T2", "09:10", "Tiếng Anh", "Phòng 8A12"),
    ("T2", "10:00", "KHTN(L)", "Phòng 8A12"),
    ("T2", "10:45", "KHTN(H)", "Phòng 8A12"),
    ("T3", "07:30", "Tiếng Anh", "Phòng 8A12"),
    ("T3", "08:15", "LS&DL(Đ)", "Phòng 8A12"),
    ("T3", "09:10", "NT(Mĩ thuật)", "Phòng 8A12"),
    ("T3", "10:00", "KHTN(H)", "Phòng 8A12"),
    ("T3", "10:45", "Tin học", "Phòng 8A12"),
    ("T4", "07:30", "NT(Nhạc)", "Phòng 8A12"),
    ("T4", "08:15", "Ngữ văn", "Phòng 8A12"),
    ("T4", "09:10", "GDTC", "Sân trường"),
    ("T4", "10:00", "Tiếng Anh", "Phòng 8A12"),
    ("T4", "10:45", "Toán", "Phòng 8A12"),
    ("T5", "07:30", "GDCD", "Phòng 8A12"),
    ("T5", "08:15", "GDĐP", "Phòng 8A12"),
    ("T5", "09:10", "LS&DL(S)", "Phòng 8A12"),
    ("T5", "10:00", "Toán", "Phòng 8A12"),
    ("T5", "10:45", "Ngữ văn", "Phòng 8A12"),
    ("T6", "07:30", "GDTC", "Sân trường"),
    ("T6", "08:15", "Toán", "Phòng 8A12"),
    ("T6", "09:10", "Công nghệ", "Phòng 8A12"),
    ("T6", "10:00", "Ngữ văn", "Phòng 8A12"),
    ("T6", "10:45", "HĐTN", "Phòng 8A12"),
    ("T7", "07:30", "HĐTN", "Phòng 8A12"),
    ("T7", "08:15", "Toán", "Phòng 8A12"),
    ("T7", "09:10", "Ngữ văn", "Phòng 8A12"),
    ("T7", "10:00", "KHTN(S)", "Phòng 8A12"),
]


def init_db():
  conn = sqlite3.connect(DB_FILE)
  cur = conn.cursor()
  cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            zalo_name TEXT,
            joined_at TEXT
        )
    """)
  cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            day_of_week TEXT,
            class_time TEXT,
            subject_name TEXT,
            room TEXT
        )
    """)
  conn.commit()

  cur.execute("SELECT COUNT(*) FROM schedule")
  if cur.fetchone()[0] == 0:
    for day, ctime, subj, room in DEFAULT_TKB_8A12:
      cur.execute(
          "INSERT INTO schedule (user_id, day_of_week, class_time, subject_name,"
          " room) VALUES (?, ?, ?, ?, ?)",
          ("default_8a12", day, ctime, subj, room),
      )
    conn.commit()
  conn.close()


def get_zalo_user(msg_obj):
  from_u = msg_obj.get("from", {})
  chat_u = msg_obj.get("chat", {})

  uid = str(from_u.get("id") or chat_u.get("id") or "unknown")
  name = (
      from_u.get("display_name")
      or from_u.get("name")
      or f"{from_u.get('first_name', '')} {from_u.get('last_name', '')}".strip()
      or from_u.get("username")
      or chat_u.get("title")
      or f"Nguyễn Hữu Nghĩa"
  )

  conn = sqlite3.connect(DB_FILE)
  cur = conn.cursor()
  cur.execute("SELECT zalo_name FROM users WHERE user_id = ?", (uid,))
  row = cur.fetchone()
  now_str = datetime.now(VN_TZ).strftime("%H:%M - %d/%m/%Y")

  if not row:
    cur.execute("INSERT INTO users VALUES (?, ?, ?)", (uid, name, now_str))
    for day, ctime, subj, room in DEFAULT_TKB_8A12:
      cur.execute(
          "INSERT INTO schedule (user_id, day_of_week, class_time, subject_name,"
          " room) VALUES (?, ?, ?, ?, ?)",
          (uid, day, ctime, subj, room),
      )
    conn.commit()
  conn.close()
  return uid, name


def build_header(zalo_name):
  return (
      f"📚 Xin chào {zalo_name}!\n"
      f"💻 Code được phát triển bởi {DEV_NAME}\n"
      f"━━━━━━━━━━━━━━━━━━━━\n"
  )


def send_message(chat_id, text):
  try:
    http_session.post(
        f"{ZALO_API_BASE}/sendMessage",
        json={"chat_id": str(chat_id), "text": text},
        timeout=8,
    )
  except Exception as e:
    print(f"[Lỗi gửi tin]: {e}")


def handle_message(item):
  msg_obj = item.get("message", item)
  chat_id = msg_obj.get("chat", {}).get("id") or msg_obj.get("from", {}).get(
      "id"
  )
  if not chat_id:
    return

  user_id, zalo_name = get_zalo_user(msg_obj)
  header = build_header(zalo_name)
  text = msg_obj.get("text", "").strip()
  text_low = text.lower()

  if text_low in ["/menu", "/start", "menu", "hi", "hello", "chào", "0"]:
    menu_text = (
        f"{header}"
        f"🎓 TRỢ LÝ THỜI KHÓA BIỂU & HỌC TẬP ({BOT_VERSION})\n"
        f"⏰ *Hệ thống tự động:*\n"
        f"  • 19:00 tối mỗi ngày: Tự động gửi danh sách môn học ngày mai 🌙\n"
        f"  • Trước giờ học 30 phút: Tự động réo tên nhắc lịch 🔔\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ DANH SÁCH LỆNH ĐIỀU KHIỂN:\n"
        f"• `/tkb` : Xem toàn bộ Thời khóa biểu lớp 8A12\n"
        f"• `/mai` : Xem ngay các môn học ngày mai\n"
        f"• `/them [Thứ] [Giờ:Phút] [Môn] [Phòng]`\n"
        f"• `/xoa [Mã]` : Xóa môn học khỏi TKB\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    send_message(chat_id, menu_text)
    return

  # Xem TKB cả tuần (Lọc bỏ trùng lặp tên môn trong cùng một ngày)
  if text_low in ["/tkb", "1"]:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, day_of_week, subject_name FROM schedule WHERE user_id = ?"
        " OR user_id = 'default_8a12' ORDER BY CASE day_of_week WHEN 'T2' THEN 1"
        " WHEN 'T3' THEN 2 WHEN 'T4' THEN 3 WHEN 'T5' THEN 4 WHEN 'T6' THEN 5"
        " WHEN 'T7' THEN 6 ELSE 7 END",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
      send_message(chat_id, f"{header}📭 Chưa có dữ liệu thời khóa biểu!")
      return

    lines = [f"{header}📅 THỜI KHÓA BIỂU LỚP 8A12 (CỦA {zalo_name.upper()}):"]
    current_day = ""
    seen_subjects = set()
    for r in rows:
      sid, day, subj = r
      if day != current_day:
        current_day = day
        lines.append(f"\n🔹 **--- {day} ---**")
        seen_subjects.clear()

      # Nếu môn học đã xuất hiện trong ngày đó thì bỏ qua không liệt kê lại nhiều lần
      if subj not in seen_subjects:
        seen_subjects.add(subj)
        lines.append(f"  • {subj}")
    send_message(chat_id, "\n".join(lines))
    return

  # Xem lịch môn học ngày mai (Chỉ hiện tên môn, không hiện giờ và phòng)
  if text_low in ["/mai", "2"]:
    now = datetime.now(VN_TZ)
    tomorrow = now + timedelta(days=1)
    day_map = {
        "Mon": "T2",
        "Tue": "T3",
        "Wed": "T4",
        "Thu": "T5",
        "Fri": "T6",
        "Sat": "T7",
        "Sun": "CN",
    }
    tom_str = day_map.get(tomorrow.strftime("%a"), "T2")

    if tom_str == "CN":
      send_message(
          chat_id,
          f"{header}🎉 Ngày mai là Chủ Nhật (CN), bạn được nghỉ học toàn"
          " tập! 🥳",
      )
      return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT subject_name FROM schedule WHERE (user_id = ? OR user_id ="
        " 'default_8a12') AND day_of_week = ?",
        (user_id, tom_str),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
      send_message(
          chat_id,
          f"{header}📭 Ngày mai ({tom_str}) không có môn học nào trong hệ"
          " thống.",
      )
      return

    # Lọc bỏ các môn bị lặp lại trong danh sách ngày mai
    unique_subjects = []
    for r in rows:
      if r[0] not in unique_subjects:
        unique_subjects.append(r[0])

    subj_list = [f"• **{subj}**" for subj in unique_subjects]
    msg = (
        f"{header}📚 CÁC MÔN HỌC NGÀY MAI ({tom_str}):\n"
        + "\n".join(subj_list)
        + "\n\n✨ Chúc bạn chuẩn bị sách vở thật tốt nhé! 💪"
    )
    send_message(chat_id, msg)
    return

  # Lệnh thêm môn học
  if text_low.startswith("/them "):
    parts = text.split(maxsplit=4)
    if len(parts) < 5:
      send_message(
          chat_id,
          f"{header}⚠️ Cú pháp chưa đúng!\n👉 Đúng: `/them [Thứ] [Giờ:Phút]"
          " [Môn] [Phòng]`",
      )
      return

    day = parts[1].upper()
    ctime = parts[2]
    subj = parts[3]
    room = parts[4]

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO schedule (user_id, day_of_week, class_time, subject_name,"
        " room) VALUES (?, ?, ?, ?, ?)",
        (user_id, day, ctime, subj, room),
    )
    conn.commit()
    conn.close()

    send_message(
        chat_id,
        f"{header}✅ ĐÃ THÊM MÔN HỌC THÀNH CÔNG!\n📅 Thứ: {day} | 📖 Môn: {subj}",
    )
    return

  # Lệnh xóa môn
  if text_low.startswith("/xoa "):
    raw_id = text.split()[1].lstrip("#") if len(text.split()) > 1 else ""
    if not raw_id.isdigit():
      send_message(chat_id, f"{header}⚠️ Vui lòng nhập mã môn học cần xóa.")
      return
    iid = int(raw_id)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM schedule WHERE id = ? AND (user_id = ? OR user_id ="
        " 'default_8a12')",
        (iid, user_id),
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    send_message(
        chat_id,
        f"{header}"
        + (
            f"🗑️ Đã xóa môn học mã #{iid} thành công!"
            if deleted
            else f"❌ Không tìm thấy mã #{iid}."
        ),
    )
    return

  send_message(
      chat_id,
      f"{header}🤖 Gõ `/menu` để mở bảng điều khiển hoặc `/mai` để xem danh"
      " sách môn học ngày mai nhé!",
  )


# ================= 4. RADAR TỰ ĐỘNG THÔNG BÁO 19:00 VÀ TRƯỚC 30 PHÚT =================
def background_scheduler():
  last_evening_date = ""
  notified_cache = set()

  while True:
    now = datetime.now(VN_TZ)
    hm = now.strftime("%H:%M")
    today_date_str = now.strftime("%Y-%m-%d")

    # 1. Tự động báo danh sách môn học ngày mai lúc 19:00 (7h tối) - Chỉ hiển thị tên môn
    if hm == "19:00" and last_evening_date != today_date_str:
      last_evening_date = today_date_str
      tomorrow = now + timedelta(days=1)
      day_map = {
          "Mon": "T2",
          "Tue": "T3",
          "Wed": "T4",
          "Thu": "T5",
          "Fri": "T6",
          "Sat": "T7",
          "Sun": "CN",
      }
      tom_str = day_map.get(tomorrow.strftime("%a"), "T2")

      if tom_str != "CN":
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_id, zalo_name FROM users")
        users = cur.fetchall()

        for uid, zname in users:
          cur.execute(
              "SELECT subject_name FROM schedule WHERE (user_id = ? OR user_id ="
              " 'default_8a12') AND day_of_week = ?",
              (uid, tom_str),
          )
          rows = cur.fetchall()
          if rows:
            unique_subs = []
            for r in rows:
              if r[0] not in unique_subs:
                unique_subs.append(r[0])

            subj_list = [f"• **{subj}**" for subj in unique_subs]
            evening_msg = (
                f"🌙 THÔNG BÁO CÁC MÔN HỌC NGÀY MAI ({tom_str})!\n"
                f"💻 Code được phát triển bởi {DEV_NAME}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Học viên: {zname}\n"
                f"📖 Môn học:\n" + "\n".join(subj_list) + f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🎒 Chúc {zname} chuẩn bị bài tập thật tốt và ngủ ngon"
                f" nhé! 💤"
            )
            send_message(uid, evening_msg)
        conn.close()

    # 2. Tự động nhắc nhở trước 30 phút cho từng môn học
    current_day_map = {
        "Mon": "T2",
        "Tue": "T3",
        "Wed": "T4",
        "Thu": "T5",
        "Fri": "T6",
        "Sat": "T7",
        "Sun": "CN",
    }
    today_str = current_day_map.get(now.strftime("%a"), "T2")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, zalo_name, day_of_week, class_time, subject_name,"
        " room FROM schedule"
    )
    all_schedules = cur.fetchall()
    conn.close()

    for sid, uid, zname, day, ctime, subj, room in all_schedules:
      if day == today_str:
        try:
          if ":" in ctime:
            hour, minute = map(int, ctime.split(":"))
            class_dt = now.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            reminder_dt = class_dt - timedelta(minutes=30)
            cache_key = f"{today_date_str}_{sid}_{uid}"

            if reminder_dt <= now < class_dt and cache_key not in notified_cache:
              notified_cache.add(cache_key)
              alert_msg = (
                  f"🚨 THÔNG BÁO LỊCH HỌC SẮP DIỄN RA!\n"
                  f"💻 Code được phát triển bởi {DEV_NAME}\n"
                  f"━━━━━━━━━━━━━━━━━━━━\n"
                  f"👤 Học viên: {zname}\n"
                  f"📖 Môn học: **{subj}**\n"
                  f"⏰ Giờ học: **{ctime}** (Còn đúng 30 phút nữa!)\n"
                  f"🏫 Phòng học: **{room}**\n"
                  f"━━━━━━━━━━━━━━━━━━━━\n"
                  f"⚡ Nhanh chóng chuẩn bị sách vở nhé!"
              )
              send_message(uid, alert_msg)
        except Exception:
          pass

    if len(notified_cache) > 200:
      notified_cache.clear()

    time.sleep(30)


# ================= 5. CỔNG WEB KEEP-ALIVE 24/7 (RENDER) =================
class KeepAliveHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()
    self.wfile.write(
        f"<html><body><h1>📚 Bot TKB Clean Online 24/7</h1><h3>Dev:"
        f" {DEV_NAME}</h3></body></html>".encode("utf-8")
    )

  def do_HEAD(self):
    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()

  def log_message(self, format, *args):
    pass


def run_web():
  try:
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), KeepAliveHandler).serve_forever()
  except Exception:
    pass


# ================= 6. MAIN RUNNER =================
def main():
  print("==========================================================")
  print(f"📚 KHỞI ĐỘNG BOT TKB CLEAN - {BOT_VERSION.upper()}")
  print(f"👨‍💻 CODE ĐƯỢC PHÁT TRIỂN BỞI: {DEV_NAME.upper()}")
  print("==========================================================")

  init_db()
  try:
    http_session.post(f"{ZALO_API_BASE}/deleteWebhook", json={}, timeout=5)
  except Exception:
    pass

  threading.Thread(target=background_scheduler, daemon=True).start()
  threading.Thread(target=run_web, daemon=True).start()

  print("🤖 Bot TKB v17.2 Clean đã sẵn sàng trực tuyến!")

  while True:
    try:
      resp = http_session.post(
          f"{ZALO_API_BASE}/getUpdates", json={"timeout": "25"}, timeout=30
      )
      data = resp.json()
      if data.get("ok") and data.get("result"):
        res = data["result"]
        events = [res] if isinstance(res, dict) else res
        for item in events:
          threading.Thread(
              target=handle_message, args=(item,), daemon=True
          ).start()
    except requests.exceptions.ReadTimeout:
      pass
    except Exception as e:
      print(f"[Lỗi kết nối Zalo]: {e}")
      time.sleep(2)


if __name__ == "__main__":
  main()