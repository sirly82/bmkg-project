import sys
from pathlib import Path

# ============================================================
# 1. MENYIAPKAN IMPORT
# ============================================================
WEBSITE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEBSITE_DIR))

import numpy as np
import pandas as pd

from modules.weather_service import get_hours_data
from modules.model_utils import load_model, predict_phenomenon

print("=" * 60)
print("PENGUJIAN PREDIKSI MODEL")
print("=" * 60)

# ============================================================
# 2. PERIKSA MODEL
# ============================================================
model, selected_features, label_map = load_model()

print("\nFitur model     :", list(selected_features))
print("Jumlah fitur    :", len(selected_features))
print("Kelas           :", list(label_map.keys()))

old_names = {"cloud_low_cover_1", "cloud_cover_oktas_m", "temp_wetbulb_c"}
stale = old_names & set(selected_features)
assert not stale, (
    f"Model masih memakai fitur lama {stale}. "
    "Train ulang dan export ulang .joblib dengan fitur baru."
)

# ============================================================
# 3. AMBIL DATA OBSERVASI
# ============================================================
selected_wib = "2025-01-01 07:00:00+07:00"

print("\nMengambil data observasi...")
df = get_hours_data(selected_wib)

if df.empty:
    raise SystemExit("GAGAL: data observasi tidak ditemukan (cek Ogimet / database).")

print(f"Jumlah data tersedia: {len(df)}")

# ============================================================
# 4. PREDIKSI SETIAP JAM (butuh riwayat 3 jam sebelumnya)
# ============================================================
ok, skipped = [], []
for ts in df["data_timestamp"]:
    try:
        ok.append((ts, predict_phenomenon(df, target_timestamp=ts)))
    except ValueError as e:
        skipped.append((ts, str(e)))

print(f"\nBerhasil diprediksi: {len(ok)} | dilewati: {len(skipped)}")
for ts, msg in skipped:
    print("  dilewati", ts, "->", msg)

if not ok:
    raise SystemExit("Tidak ada jam yang bisa diprediksi.")

# ============================================================
# 5. HASIL JAM TERAKHIR
# ============================================================
ts, result = ok[-1]
print("\nJam diuji (UTC):", ts)
print("Fenomena prediksi :", result["predicted_class"])
print("Confidence        :", f"{result['confidence']:.2%}")
print("\nProbabilitas:")
for name, prob in result["probabilities"].items():
    print(f"{name:<30} : {prob:.2%}")

feats = result["features"]
assert list(feats.columns) == list(selected_features)
assert not feats.isna().any().any()
assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-6
assert result["predicted_class"] in label_map

# ============================================================
# 6. TABEL SEMUA PREDIKSI
# ============================================================
aktual = df.set_index("data_timestamp")["phenomenon"]
vis = df.set_index("data_timestamp")["visibility_vv"]
print("\n" + pd.DataFrame([
    {
        "utc": t,
        "prediksi": r["predicted_class"],
        "confidence": f"{r['confidence']:.0%}",
        "aktual_ww": aktual.get(t),
        "vis_km": vis.get(t),
    }
    for t, r in ok
]).to_string(index=False))

# ============================================================
# 7. DATA TIDAK LENGKAP HARUS DITOLAK
# ============================================================
bad = df.copy()
bad.loc[bad.index[-1], "visibility_vv"] = np.nan
try:
    predict_phenomenon(bad, target_timestamp=bad["data_timestamp"].iloc[-1])
    raise AssertionError("Data tidak lengkap seharusnya ditolak!")
except ValueError as e:
    print("\nData tidak lengkap ditolak dengan benar:", e)

print("\nPengujian selesai.")