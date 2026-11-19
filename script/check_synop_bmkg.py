import pandas as pd
import numpy as np

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 60)

# =========================
# 1. KONFIGURASI
# =========================
PATH_SYNOP = "stamet_jambi_hour_full_2026.csv"   # ganti sesuai nama file
PATH_BMKG  = "bmkg-jambi-26.csv"           # ganti sesuai nama file

COL_DT_SYNOP = "data_timestamp"   # nama kolom datetime di file SYNOP
COL_DT_BMKG  = "data_timestamp"   # nama kolom datetime di file BMKG

TOLERANSI = 1e-6   # selisih numerik <= ini dianggap sama (naikkan jika perlu, mis. 0.1)

# kolom yang tidak perlu dibandingkan (metadata, dll.)
KOLOM_ABAIKAN = ["station_name", "created_at", "updated_at",
                 "qc_flag", "qc_histories", "observer_name", "raw_synop"]

# =========================
# 2. LOAD DATA
# =========================
df_synop = pd.read_csv(PATH_SYNOP)
df_bmkg  = pd.read_csv(PATH_BMKG)

# samakan nama kolom datetime & ubah ke tipe datetime
df_synop = df_synop.rename(columns={COL_DT_SYNOP: "datetime"})
df_bmkg  = df_bmkg.rename(columns={COL_DT_BMKG: "datetime"})

print("Contoh datetime SYNOP:", df_synop["datetime"].head(3).tolist())
print("Contoh datetime BMKG :", df_bmkg["datetime"].head(3).tolist())

FORMAT_SYNOP = None
FORMAT_BMKG  = None

def parse_dt(series, fmt, nama):
    s = series.astype(str).str.strip()
    dt = pd.to_datetime(s, format=fmt, errors="coerce", utc=True)  # utc=True biar aman kalau ada +00:00
    gagal = dt.isna().sum()
    if gagal > 0:
        print(f"⚠️ {nama}: {gagal} baris gagal diparse, contoh:", series[dt.isna()].head(5).tolist())
    return dt.dt.tz_localize(None)   # buang info timezone, nilai tetap sama

df_synop["datetime"] = parse_dt(df_synop["datetime"], FORMAT_SYNOP, "SYNOP")
df_bmkg["datetime"]  = parse_dt(df_bmkg["datetime"],  FORMAT_BMKG,  "BMKG")

# buang baris yang datetime-nya gagal diparse
df_synop = df_synop.dropna(subset=["datetime"])
df_bmkg  = df_bmkg.dropna(subset=["datetime"])

# =========================
# 3. CEK DUPLIKAT DATETIME
# =========================
print(f"\nDuplikat datetime -> SYNOP: {df_synop['datetime'].duplicated().sum()}, "
      f"BMKG: {df_bmkg['datetime'].duplicated().sum()}")

df_synop = df_synop.drop_duplicates("datetime", keep="last").set_index("datetime").sort_index()
df_bmkg  = df_bmkg.drop_duplicates("datetime", keep="last").set_index("datetime").sort_index()

# =========================
# 4. CEK KECOCOKAN DATETIME & KOLOM
# =========================
# Hanya datetime milik SYNOP yang dicek. Baris BMKG di luar itu diabaikan.
dt_sama     = df_synop.index.intersection(df_bmkg.index)     # ada di dua file
hanya_synop = df_synop.index.difference(df_bmkg.index)       # ada di SYNOP, tidak ada di BMKG
hanya_bmkg  = pd.DatetimeIndex([])                           # sengaja diabaikan

kolom_sama = [c for c in df_synop.columns
              if c in df_bmkg.columns and c not in KOLOM_ABAIKAN]

print(f"\nRentang SYNOP : {df_synop.index.min()} s/d {df_synop.index.max()} ({len(df_synop)} baris)")
print(f"Rentang BMKG  : {df_bmkg.index.min()} s/d {df_bmkg.index.max()} ({len(df_bmkg)} baris)")
print(f"Baris BMKG di luar rentang SYNOP (diabaikan): "
      f"{(~df_bmkg.index.isin(df_synop.index)).sum()}")
print(f"Datetime SYNOP yang ketemu di BMKG : {len(dt_sama)}")
print(f"Datetime SYNOP yang TIDAK ada di BMKG: {len(hanya_synop)}")
print(f"Kolom yang dibandingkan ({len(kolom_sama)}): {kolom_sama}")

if len(dt_sama) == 0:
    raise ValueError("Tidak ada datetime yang sama. Cek rentang tanggal atau timezone-nya (UTC vs WIB).")

# =========================
# 4b. KHUSUS: JUMLAHKAN CLOUD LOW COVER DI BMKG
# =========================
KOLOM_JUMLAH = {
    "cloud_low_cover_1": ["cloud_low_cover_1", "cloud_low_cover_2", "cloud_low_cover_3"],
}
BATAS_MAKS = None   # isi 8 kalau mau hasil jumlah dibatasi maksimal 8 oktas, None = tanpa batas

df_bmkg_asli = df_bmkg.copy()   # simpan versi asli untuk keterangan

for target, komponen in KOLOM_JUMLAH.items():
    komponen_ada = [c for c in komponen if c in df_bmkg.columns]
    angka = df_bmkg[komponen_ada].apply(pd.to_numeric, errors="coerce")

    # NaN dianggap 0 saat dijumlah, tapi kalau SEMUA komponen NaN hasilnya tetap NaN
    jumlah = angka.sum(axis=1, min_count=1)

    if BATAS_MAKS is not None:
        jumlah = jumlah.clip(upper=BATAS_MAKS)

    print(f"\n{target} (BMKG) = {' + '.join(komponen_ada)}")
    print(f"  Baris yang jumlahnya > 8: {(jumlah > 8).sum()}")
    df_bmkg[target] = jumlah

# =========================
# 5. BANDINGKAN PER KOLOM
# =========================
a = df_synop.loc[dt_sama, kolom_sama]
b = df_bmkg.loc[dt_sama, kolom_sama]

hasil = []
for col in kolom_sama:
    va, vb = a[col], b[col]

    # coba bandingkan sebagai angka
    na, nb = pd.to_numeric(va, errors="coerce"), pd.to_numeric(vb, errors="coerce")
    numerik = (na.notna().sum() >= va.notna().sum() * 0.9) and (nb.notna().sum() >= vb.notna().sum() * 0.9)

    if numerik:
        selisih = na - nb
        beda_nilai = selisih.abs() > TOLERANSI
        beda_nan   = na.isna() != nb.isna()          # satu NaN, satunya ada nilai
        beda = (beda_nilai & na.notna() & nb.notna()) | beda_nan
        jenis = np.where(beda_nan, "salah satu NaN", "nilai beda")
        pct = (selisih / nb.replace(0, np.nan) * 100).round(2)
        out = pd.DataFrame({
            "kolom": col, "nilai_synop": na, "nilai_bmkg": nb,
            "selisih (synop-bmkg)": selisih, "selisih_%": pct, "jenis_beda": jenis
        })[beda]
    else:
        sa = va.astype("string").str.strip().str.lower()
        sb = vb.astype("string").str.strip().str.lower()
        beda_nan = sa.isna() != sb.isna()
        beda = ((sa != sb) & sa.notna() & sb.notna()) | beda_nan
        jenis = np.where(beda_nan, "salah satu NaN", "nilai beda")
        out = pd.DataFrame({
            "kolom": col, "nilai_synop": va, "nilai_bmkg": vb,
            "selisih (synop-bmkg)": np.nan, "selisih_%": np.nan, "jenis_beda": jenis
        })[beda]

    hasil.append(out)

df_beda = (pd.concat(hasil)
             .reset_index()                       # datetime jadi kolom
             .sort_values(["datetime", "kolom"])
             .reset_index(drop=True))

# DIAGNOSTIK: cek geseran jam antara SYNOP dan BMKG
for geser in [-7, -1, 0, 1, 7]:
    s = df_synop.copy()
    s.index = s.index + pd.Timedelta(hours=geser)
    idx = s.index.intersection(df_bmkg.index)
    cocok = []
    for col in kolom_sama:
        x = pd.to_numeric(s.loc[idx, col], errors="coerce")
        y = pd.to_numeric(df_bmkg.loc[idx, col], errors="coerce")
        if x.notna().any():
            cocok.append(((x - y).abs() <= TOLERANSI).mean())
    if cocok:
        print(f"geser {geser:+d} jam -> baris ketemu: {len(idx)}, rata-rata % cocok: {np.mean(cocok)*100:.1f}%")

# =========================
# 6. URUTKAN PER KOLOM, LALU PER DATETIME
# =========================
urutan_kolom = {c: i for i, c in enumerate(kolom_sama)}
df_beda["_urut"] = df_beda["kolom"].map(urutan_kolom)
df_beda = (df_beda.sort_values(["_urut", "datetime"])
                  .drop(columns="_urut")
                  .reset_index(drop=True))

# tambahkan raw_synop berdasarkan datetime
if "raw_synop" in df_synop.columns:
    df_beda["raw_synop"] = df_beda["datetime"].map(df_synop["raw_synop"])
else:
    print("⚠️ Kolom 'raw_synop' tidak ditemukan di file SYNOP, dilewati.")
    df_beda["raw_synop"] = np.nan

# keterangan komponen penjumlahan (hanya untuk kolom yang dijumlahkan)
def keterangan_komponen(row):
    if row["kolom"] in KOLOM_JUMLAH:
        komp = [c for c in KOLOM_JUMLAH[row["kolom"]] if c in df_bmkg_asli.columns]
        nilai = df_bmkg_asli.loc[row["datetime"], komp]
        return " + ".join(f"{c.replace('cloud_low_cover_', 'cl')}={v}" for c, v in nilai.items())
    return np.nan

if len(df_beda) > 0:
    df_beda["komponen_bmkg"] = df_beda.apply(keterangan_komponen, axis=1)
else:
    df_beda["komponen_bmkg"] = np.nan

# susun ulang kolom: bmkg dulu, lalu synop, komponen, raw_synop paling akhir
df_beda = df_beda[["kolom", "datetime", "nilai_bmkg", "nilai_synop",
                   "selisih (synop-bmkg)", "selisih_%", "jenis_beda",
                   "komponen_bmkg", "raw_synop"]]

# ringkasan per kolom
ringkas = []
for col in kolom_sama:
    sub = df_beda[df_beda["kolom"] == col]
    n_beda = len(sub)
    nilai = sub[sub["jenis_beda"] == "nilai beda"]
    mae = pd.to_numeric(nilai["selisih (synop-bmkg)"], errors="coerce").abs().mean()
    ringkas.append({
        "kolom": col,
        "jumlah_dibandingkan": len(dt_sama),
        "jumlah_beda": n_beda,
        "persen_beda": round(n_beda / len(dt_sama) * 100, 2),
        "MAE_selisih": round(mae, 4) if pd.notna(mae) else np.nan,
    })
df_ringkas = pd.DataFrame(ringkas)

print("=== RINGKASAN PER KOLOM ===")
print(df_ringkas.to_string(index=False))

MAKS_TAMPIL = 20   # batasi baris yang dicetak per kolom (file lengkap tetap disimpan)
TAMPILKAN_RAW_DI_TERMINAL = False   # True kalau mau raw_synop ikut tercetak

# cetak detail per kolom
for col in kolom_sama:
    sub = df_beda[df_beda["kolom"] == col].drop(columns="kolom")
    if not TAMPILKAN_RAW_DI_TERMINAL:
        sub = sub.drop(columns="raw_synop")
    print(f"\n{'='*70}\n{col}  ->  {len(sub)} baris beda\n{'='*70}")
    if col not in KOLOM_JUMLAH:
        sub = sub.drop(columns="komponen_bmkg")
    if sub.empty:
        print("(tidak ada perbedaan)")
    else:
        print(sub.head(MAKS_TAMPIL).to_string(index=False))
        if len(sub) > MAKS_TAMPIL:
            print(f"... dan {len(sub) - MAKS_TAMPIL} baris lainnya (lihat file hasil)")

# =========================
# 7. SIMPAN
# =========================
# a) satu file CSV berisi semua perbedaan (sudah terurut per kolom lalu datetime)
df_ringkas.to_csv("perbandingan_ringkasan.csv", index=False)
df_beda.to_csv("perbandingan_detail_beda.csv", index=False)

# b) satu file CSV per kolom (opsional, hapus kalau tidak perlu)
import os
os.makedirs("perbandingan_per_kolom", exist_ok=True)
for col in kolom_sama:
    sub = df_beda[df_beda["kolom"] == col].drop(columns="kolom")
    if not sub.empty:
        sub.to_csv(f"perbandingan_per_kolom/{col}.csv", index=False)

print("\nTersimpan: perbandingan_ringkasan.csv, perbandingan_detail_beda.csv, folder perbandingan_per_kolom/")