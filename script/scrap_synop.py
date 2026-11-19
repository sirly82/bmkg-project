import http.cookiejar
import math
import re
import time
import urllib.request
from html.parser import HTMLParser
import numpy as np
import pandas as pd

class OgimetTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.rows = []
        self.current_row = []
        self.current_cell = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_tr:
            self.in_td = True
            self.current_cell = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("td", "th") and self.in_td:
            self.in_td = False
            cell_text = " ".join("".join(self.current_cell).split())
            self.current_row.append(cell_text)
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            if self.current_row:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_td:
            self.current_cell.append(data)

def decode_visibility_km(vv_str):
    if not vv_str.isdigit():
        return None
    vv = int(vv_str)
    if 0 <= vv <= 50:
        return round(vv * 0.1, 2)
    elif 56 <= vv <= 80:
        return float(vv - 50)
    elif 81 <= vv <= 88:
        return float(30 + (vv - 80) * 5)
    elif vv == 89:
        return 70.0
    elif 90 <= vv <= 99:
        table_90 = {
            90: 0.05, 91: 0.05, 92: 0.2, 93: 0.5, 94: 1.0,
            95: 2.0, 96: 4.0, 97: 10.0, 98: 20.0, 99: 50.0,
        }
        return table_90.get(vv)
    return None

def classify_phenomenon(ww_code, ix_flag=None):
    # Jika WW kosong, periksa alasan kelompok WW tidak dilaporkan.
    if pd.isna(ww_code) or str(ww_code).strip() == "":
        if pd.notna(ix_flag):
            ix = str(ix_flag).strip()
            if ix in {"2", "5"}:
                return "Normal"
        return "Unknown"

    # Validasi kode WW.
    try:
        ww_value = float(str(ww_code).strip())

        if not math.isfinite(ww_value) or not ww_value.is_integer():
            return "Unknown"

        ww = int(ww_value)
    except (ValueError, TypeError):
        return "Unknown"

    if not 0 <= ww <= 99:
        return "Unknown"

    # Klasifikasi fenomena berdasarkan kode WW.
    if 0 <= ww <= 3:
        return "Normal"
    elif 4 <= ww <= 9 or 30 <= ww <= 35:
        return "Haze/Smoke/Dust"
    elif ww == 10:
        return "Mist"
    elif ww in {11, 12, 28} or 40 <= ww <= 49:
        return "Fog"
    elif 50 <= ww <= 99:
        return "Active Precipitation"
    elif 14 <= ww <= 17 or 20 <= ww <= 27 or ww == 29:
        return "Recent/Distant Precipitation"
    else:
        return "Other"

def calc_wetbulb_stull(temp_c, rh_pct):
    if temp_c is None or rh_pct is None:
        return None
    tw = (
        temp_c * math.atan(0.151977 * math.sqrt(rh_pct + 8.313659))
        + math.atan(temp_c + rh_pct)
        - math.atan(rh_pct - 1.676331)
        + 0.00391838 * (rh_pct ** 1.5) * math.atan(0.023101 * rh_pct)
        - 4.686035
    )
    return round(tw, 1)

def parse_synop_row(row):
    date_match = None
    idx_aaxx = None

    for i, cell in enumerate(row):
        if date_match is None:
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", cell)
            if m:
                date_match = m
        if idx_aaxx is None and cell.startswith("AAXX"):
            idx_aaxx = i

    if date_match is None or idx_aaxx is None or idx_aaxx + 1 >= len(row):
        return None

    dd, mm, yyyy, hh, mi = date_match.groups()
    report_type = row[0] if row else None
    raw = f"{row[idx_aaxx]} {row[idx_aaxx + 1]}".strip()

    if "NIL" in raw:
        return None

    tokens = raw.replace("=", "").split()
    if len(tokens) < 5:
        return None

    header_time = tokens[1]
    wind_unit_code = header_time[-1] if len(header_time) >= 5 else "4"
    is_knots = wind_unit_code in ("3", "4")

    grp_vis = tokens[3]   # iR ix h VV
    grp_wind = tokens[4]  # N dd ff

    ir_flag = grp_vis[0] if len(grp_vis) == 5 else None
    ix_flag = grp_vis[1] if len(grp_vis) == 5 else None
    vis_km = decode_visibility_km(grp_vis[3:5]) if len(grp_vis) == 5 else None

    if grp_wind[1:3] == "99":
        wind_dir = None
    elif grp_wind[1:3].isdigit():
        wind_dir = int(grp_wind[1:3]) * 10
    else:
        wind_dir = None

    wind_raw = int(grp_wind[3:5]) if grp_wind[3:5].isdigit() else None

    cursor = 5
    if wind_raw == 99 and cursor < len(tokens) and tokens[cursor].startswith("00"):
        wind_raw = int(tokens[cursor][2:5]) if tokens[cursor][2:5].isdigit() else None
        cursor += 1

    wind_kt = int(round(wind_raw if is_knots else wind_raw * 1.94384)) if wind_raw is not None else None

    temp_c = dewpoint_c = stn_press = mslp = ww_code = None

    # Tutupan awan total dari Nddff
    cloud_oktas = (
        int(grp_wind[0])
        if len(grp_wind) == 5 and grp_wind[0].isdigit()
        else None
    )

    # Tutupan awan rendah dari grup 8NhCLCMCH
    cloud_low_1 = None

    for tok in tokens[cursor:]:
        if tok in ("333", "444", "555"):
            break

        if len(tok) == 5 and tok.startswith("8"):
            nh = tok[1]
            cl = tok[2]

            if cl == "0":
                # Tidak terdapat awan rendah
                cloud_low_1 = 0
            elif cl.isdigit() and nh.isdigit():
                # Awan rendah ada, gunakan nilai Nh
                cloud_low_1 = int(nh)
            else:
                cloud_low_1 = None
            
            break


    rain_mm = 0.0 if ir_flag == "3" else None
    rain_period_h = None
    rain_24h = None

    period_map = {
        "1": 6, "2": 12, "3": 18, "4": 24,
        "5": 1, "6": 2, "7": 3, "8": 9, "9": 15,
    }

    for tok in tokens[cursor:]:
        if tok in ("333", "444", "555"):
            break
        if len(tok) != 5 or not tok[1:].isdigit():
            continue

        prefix = tok[0]
        if prefix == "1" and temp_c is None:
            sign = -1 if tok[1] == "1" else 1
            temp_c = sign * int(tok[2:5]) / 10.0
        elif prefix == "2" and dewpoint_c is None:
            if tok[1] != "9":
                sign = -1 if tok[1] == "1" else 1
                dewpoint_c = sign * int(tok[2:5]) / 10.0
        elif prefix == "3" and stn_press is None:
            val = int(tok[1:5])
            stn_press = round(val / 10.0 + (1000.0 if val < 5000 else 0.0), 1)
        elif prefix == "4" and mslp is None:
            val = int(tok[1:5])
            mslp = round(val / 10.0 + (1000.0 if val < 5000 else 0.0), 1)
        elif prefix == "6" and rain_period_h is None:
            rrr = int(tok[1:4])
            tr = tok[4]
            if rrr == 0:
                rain_mm = 0.0
            elif 1 <= rrr <= 989:
                rain_mm = float(rrr)
            elif rrr == 990:
                rain_mm = 0.05
            elif 991 <= rrr <= 999:
                rain_mm = round((rrr - 990) * 0.1, 1)
            rain_period_h = period_map.get(tr)
            if tr == "4":
                rain_24h = rain_mm
        elif prefix == "7" and ww_code is None:
            ww_code = tok[1:3]

    rh_exact = None
    rh_int = None
    if temp_c is not None and dewpoint_c is not None:
        es = math.exp((17.625 * temp_c) / (243.04 + temp_c))
        e = math.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c))
        rh_exact = 100.0 * (e / es)
        rh_int = int(round(rh_exact))

    wetbulb_c = calc_wetbulb_stull(temp_c, rh_exact)
    phenomenon = classify_phenomenon(ww_code, ix_flag)

    return {
        "station_name": "Stasiun Meteorologi Sultan Thaha",
        "data_timestamp": f"{yyyy}-{mm}-{dd} {hh}:{mi}:00",
        "wind_dir_deg_dd": wind_dir,
        "wind_speed_ff": wind_kt,
        "pressure_qfe_mb_derived": stn_press,
        "pressure_qff_mb_derived": mslp,
        "temp_drybulb_c_tttttt": temp_c,
        "temp_dewpoint_c_tdtdtd": dewpoint_c,
        "temp_wetbulb_c": wetbulb_c,
        "relative_humidity_pc": rh_int,
        "cloud_low_cover_1": cloud_low_1,
        "cloud_cover_oktas_m": cloud_oktas,
        "rainfall_24h_rrrr": rain_24h,
        "rainfall_mm": rain_mm,
        "rainfall_period_h": rain_period_h,
        "ix_flag": ix_flag,
        "phenomenon": phenomenon,
        "weather_code_ww": ww_code,
        "visibility_vv": vis_km,
        "report_type": report_type,
        "raw_synop": raw,
    }

TAHUN = 2025
bulan_akhir = {
    # 1: 31, 2: 28, 3: 31,
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
}
output_file = f"stamet_jambi_hourly_full_{TAHUN}.csv"
records = []

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    ("Referer", "https://www.ogimet.com/synops.phtml.en"),
]
opener.open("https://www.ogimet.com/synops.phtml.en", timeout=30).read()

for bulan, hari_akhir in bulan_akhir.items():
    url = (
        f"https://www.ogimet.com/display_synops2.php?lang=en&lugar=96195"
        f"&wigos=&tipo=ALL&ord=ASC&nil=NO&fmt=html&ano={TAHUN}&mes={bulan:02d}&day=01&hora=00"
        f"&anof={TAHUN}&mesf={bulan:02d}&dayf={hari_akhir:02d}&horaf=23&send=send"
    )

    for attempt in range(1, 4):
        print(f"Mengunduh & decode bulan {bulan:02d}/{TAHUN} (percobaan {attempt})...")
        try:
            html_text = opener.open(url, timeout=30).read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  -> Gagal koneksi ({e}), tunggu 20 detik...")
            time.sleep(20)
            continue

        parser = OgimetTableParser()
        parser.feed(html_text)

        month_records = []
        for row in parser.rows:
            parsed = parse_synop_row(row)
            if parsed:
                month_records.append(parsed)

        if month_records:
            records.extend(month_records)
            print(f"  -> {len(month_records)} baris berhasil di-decode")

            # Simpan checkpoint otomatis setiap bulan selesai
            df_temp = pd.DataFrame(records)
            df_temp["data_timestamp"] = pd.to_datetime(df_temp["data_timestamp"])
            df_temp = (
                df_temp.sort_values("data_timestamp")
                .drop_duplicates(subset=["data_timestamp"])
                .reset_index(drop=True)
            )
            df_temp["data_timestamp"] = df_temp["data_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
            df_temp.to_csv(output_file, index=False)
            break
        else:
            jeda = 30 * attempt
            print(f"  -> 0 baris (jeda {jeda} detik lalu coba ulang)...")
            time.sleep(jeda)

    time.sleep(10)

if not records:
    raise RuntimeError("Tidak ada baris tabel SYNOP yang terbaca dari HTML.")

df = pd.read_csv(output_file)
int_cols = [
    "wind_dir_deg_dd", "wind_speed_ff", "relative_humidity_pc",
    "cloud_low_cover_1", "cloud_cover_oktas_m", "rainfall_period_h",
]
for col in int_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

df.to_csv(output_file, index=False)
print(f"\nSelesai! Total {len(df)} baris tersimpan ke {output_file}")
print("\nSebaran fenomena tahun 2025:")
print(df["phenomenon"].value_counts())