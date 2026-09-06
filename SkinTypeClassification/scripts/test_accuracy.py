
import sys
import csv
import requests
from pathlib import Path

API_URL = "http://localhost:8000/analyze-skin"

# Map folder name -> expected letter in the model's skin_type output
LABEL_MAP = {"oily": "O", "dry": "D"}
SKIP_FOLDERS = {"normal"}  # model has no normal/combination class


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_accuracy.py path/to/dataset")
        sys.exit(1)

    dataset_dir = Path(sys.argv[1])
    results = []

    for folder in dataset_dir.iterdir():
        if not folder.is_dir():
            continue
        folder_name = folder.name.lower()
        if folder_name in SKIP_FOLDERS:
            print(f"Skipping '{folder_name}' (no matching model class)")
            continue
        if folder_name not in LABEL_MAP:
            print(f"Skipping unrecognized folder '{folder_name}'")
            continue

        expected = LABEL_MAP[folder_name]
        images = [f for f in folder.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")]
        print(f"\nTesting {len(images)} images from '{folder_name}' (expected: {expected})")

        for img_path in images:
            try:
                with open(img_path, "rb") as f:
                    resp = requests.post(API_URL, files={"file": f}, timeout=30)

                if resp.status_code != 200:
                    print(f"  {img_path.name}: ERROR {resp.status_code} - {resp.text[:100]}")
                    results.append([img_path.name, folder_name, expected, "ERROR", False])
                    continue

                data = resp.json()
                skin_type = data.get("skin_type", "")
                predicted = skin_type[0] if skin_type else "?"
                correct = predicted == expected

                print(f"  {img_path.name}: predicted={predicted} ({'OK' if correct else 'WRONG'})")
                results.append([img_path.name, folder_name, expected, predicted, correct])

            except Exception as e:
                print(f"  {img_path.name}: EXCEPTION - {e}")
                results.append([img_path.name, folder_name, expected, "EXCEPTION", False])

    # Write CSV
    out_path = Path("accuracy_results.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "true_folder", "expected", "predicted", "correct"])
        writer.writerows(results)

    # Summary
    total = len(results)
    correct_count = sum(1 for r in results if r[4] is True)
    print(f"\n=== Summary ===")
    print(f"Total tested: {total}")
    print(f"Correct: {correct_count}")
    print(f"Accuracy: {correct_count / total * 100:.1f}%" if total else "No images tested")
    print(f"Full results saved to {out_path.resolve()}")


if __name__ == "__main__":
    main()