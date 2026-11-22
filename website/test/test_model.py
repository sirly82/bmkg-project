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
from modules.model_utils import (
    classify_phenomenon_at,
    load_classifier_model,
    load_forecast_model,
    predict_next_hour_phenomenon,
)

print("=" * 65)
print("PENGUJIAN MODEL KLASIFIKASI (t) & PREDIKSI (t+1)")
print("=" * 65)

# ============================================================
# 2. PERIKSA KEDUA MODEL
# ============================================================
clf_model, clf_features, clf_labels = load_classifier_model()
fc_model, fc_features, fc_labels = load_forecast_model()

print("\n[Model 1 - Klasifikasi t (LightGBM)]")
print("Jumlah fitur :", len(clf_features))
print("Kelas        :", list(clf_labels.keys()))

print("\n[Model 2 - Prediksi t+1 (XGBoost)]")
print("Jumlah fitur :", len(fc_features))
print("Fitur now_*  :", [f for f in fc_features if f.startswith("now_")])
print("Kelas        :", list(fc_labels.keys()))

old_names = {"cloud_low_cover_1", "cloud_cover_oktas_m", "temp_wetbulb_c"}
assert not (old_names & set(clf_features)), "Model klasifikasi masih memakai fitur lama!"
assert not (old_names & set(fc_features)), "Model prediksi masih memakai fitur lama!"
assert len([f for f in fc_features if f.startswith("now_")]) == 7, "Fitur one-hot now_* harus 7!"

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
# 4. UJI KLASIFIKASI (t) SETIAP JAM
# ============================================================
ok_clf, skipped_clf = [], []
for ts in df["data_timestamp"]:
    try:
        ok_clf.append((ts, classify_phenomenon_at(df, target_timestamp=ts)))
    except ValueError as e:
        skipped_clf.append((ts, str(e)))

print(f"\n[Klasifikasi t] Berhasil: {len(ok_clf)} | Dilewati: {len(skipped_clf)}")
if not ok_clf:
    raise SystemExit("Tidak ada jam yang bisa diklasifikasi.")

ts_last, res_clf = ok_clf[-1]
print("\nJam diuji klasifikasi (UTC):", ts_last)
print("Hasil klasifikasi (t)      :", res_clf["predicted_class"])
print("Confidence                 :", f"{res_clf['confidence']:.2%}")

feats_clf = res_clf["features"]
assert list(feats_clf.columns) == list(clf_features)
assert not feats_clf.isna().any().any()
assert abs(sum(res_clf["probabilities"].values()) - 1.0) < 1e-6

# ============================================================
# 5. UJI PREDIKSI 1 JAM KE DEPAN (t+1)
# ============================================================
# Uji pada jam kedua terakhir (23:00 UTC) agar bisa dibandingkan dengan aktual 00:00 UTC,
# serta pada jam terakhir (00:00 UTC) untuk memprediksi 01:00 UTC.
aktual_by_ts = df.set_index("data_timestamp")["phenomenon"]

print("\n" + "-" * 65)
print("PENGUJIAN PREDIKSI 1 JAM KE DEPAN (t+1)")
print("-" * 65)

test_indices = [-2, -1] if len(df) >= 2 else [-1]
for idx in test_indices:
    base_ts = df["data_timestamp"].iloc[idx]
    res_fc = predict_next_hour_phenomenon(df, target_timestamp=base_ts)
    target_ts = res_fc["forecast_timestamp_utc"]
    aktual_next = aktual_by_ts.get(target_ts, "(Belum tersedia di df)")

    feats_fc = res_fc["features"]
    assert list(feats_fc.columns) == list(fc_features)
    assert abs(sum(res_fc["probabilities"].values()) - 1.0) < 1e-6
    assert res_fc["predicted_class"] in fc_labels

    # Pastikan tepat satu kolom now_* bernilai 1
    now_cols = [f for f in fc_features if f.startswith("now_")]
    assert int(feats_fc[now_cols].sum(axis=1).iloc[0]) == 1

    print(f"\nBasis observasi (t)   : {base_ts} UTC")
    print(f"Input fenomena (t)    : {res_fc['input_phenomenon_t']} ({res_fc['input_phenomenon_source']})")
    print(f"Target prediksi (t+1) : {target_ts} UTC")
    print(f"Prediksi (t+1)        : {res_fc['predicted_class']} ({res_fc['confidence']:.2%})")
    print(f"Aktual SYNOP (t+1)    : {aktual_next}")
    print("Top 3 Probabilitas (t+1):")
    for name, prob in list(res_fc["probabilities"].items())[:3]:
        print(f"  - {name:<28} : {prob:.2%}")

# ============================================================
# 6. UJI FALLBACK KETIKA PHENOMENON (t) == 'Unknown'
# ============================================================
unknown_df = df.copy()
unknown_df.loc[unknown_df.index[-1], "phenomenon"] = "Unknown"
unknown_df.loc[unknown_df.index[-1], "weather_code_ww"] = None
unknown_df.loc[unknown_df.index[-1], "ix_flag"] = "3"

res_fb = predict_next_hour_phenomenon(
    unknown_df,
    target_timestamp=unknown_df["data_timestamp"].iloc[-1],
)
assert res_fb["input_phenomenon_source"] == "classified_fallback"
print(
    "\nFallback 'Unknown' berhasil -> memakai hasil klasifikasi:",
    res_fb["input_phenomenon_t"],
    "-> prediksi t+1:",
    res_fb["predicted_class"],
)

# ============================================================
# 7. DATA TIDAK LENGKAP HARUS DITOLAK
# ============================================================
bad = df.copy()
bad.loc[bad.index[-1], "visibility_vv"] = np.nan

for fn_name, fn in [
    ("classify_phenomenon_at", classify_phenomenon_at),
    ("predict_next_hour_phenomenon", predict_next_hour_phenomenon),
]:
    try:
        fn(bad, target_timestamp=bad["data_timestamp"].iloc[-1])
        raise AssertionError(f"{fn_name}: Data tidak lengkap seharusnya ditolak!")
    except ValueError as e:
        print(f"Validasi {fn_name} menolak data kosong dengan benar: {e}")

print("\nSemua pengujian model klasifikasi (t) dan prediksi (t+1) berhasil.")