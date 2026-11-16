import joblib
from pathlib import Path

MODEL_PATH = Path("model/visibility_rf_model.pkl")

print("Memuat model...")
model_data = joblib.load(MODEL_PATH)

print("\n" + "=" * 60)
print("STRUKTUR FILE MODEL")
print("=" * 60)

print("\nTipe objek utama:", type(model_data))

if isinstance(model_data, dict):

    print("\nDaftar key dalam dictionary:")

    for key, value in model_data.items():
        print(f"\nKey       : {key}")
        print(f"Tipe      : {type(value)}")

        # Jika berupa dictionary lagi
        if isinstance(value, dict):
            print("Isi key   :", list(value.keys()))

        # Jika berupa list atau tuple
        elif isinstance(value, (list, tuple)):
            print("Panjang   :", len(value))

        # Jika berupa objek model Scikit-learn
        if hasattr(value, "n_features_in_"):
            print("Jumlah fitur:", value.n_features_in_)

        if hasattr(value, "feature_names_in_"):
            print("Nama fitur :", value.feature_names_in_)

        if hasattr(value, "classes_"):
            print("Kelas      :", value.classes_)

        if hasattr(value, "predict_proba"):
            print("predict_proba:", True)

        if hasattr(value, "get_params"):
            print("Parameter  :", value.get_params())
else:
    print("\nFile bukan dictionary.")
    print("Tipe objek:", type(model_data))

print("\n" + "=" * 60)
print("DETAIL METADATA MODEL")
print("=" * 60)

print("\nSelected features:")
print(model_data["selected_features"])

print("\nLabel map:")
for key, value in model_data["label_map"].items():
    print(f"{key!r} -> {value!r}")