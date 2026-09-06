"""
retrain_sensitive.py — Retrain the sensitive/resistant skin classifier.

Usage:
    python retrain_sensitive.py <dataset_root> <output_model_path>

Where <dataset_root> must contain subfolders:
    <dataset_root>/train/sensitive/   (images of sensitive skin)
    <dataset_root>/train/resistant/   (images of resistant skin)
    <dataset_root>/valid/sensitive/
    <dataset_root>/valid/resistant/

Label convention (matches app.py):
    sensitive → output near 1.0  (model score > 0.3  ⟹ "S")
    resistant → output near 0.0  (model score ≤ 0.3  ⟹ "R")

Example:
    python retrain_sensitive.py ./data/sensitive_dataset app/models/sensitive_resistant_model.h5
"""

import sys
import tensorflow as tf

IMG_SIZE        = (224, 224)
BATCH_SIZE      = 16
EPOCHS          = 10
FINE_TUNE_EPOCHS = 10


def load_dataset(root_dir: str, split: str, augment: bool = False):
    """
    Load a sensitive/resistant image dataset from disk.

    Expects subfolders named exactly 'sensitive' and 'resistant'.
    Returns a tf.data.Dataset with pixels normalised to [0, 1],
    label=1.0 for sensitive, label=0.0 for resistant.
    """
    ds = tf.keras.utils.image_dataset_from_directory(
        f"{root_dir}/{split}",
        labels="inferred",
        label_mode="int",
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=(split == "train"),
    )
    class_names = ds.class_names
    print(f"  [{split}] detected classes (alphabetical): {class_names}")

    sensitive_idx = class_names.index("sensitive")
    resistant_idx = class_names.index("resistant")  # noqa: F841 (used implicitly via != sensitive)

    # Remap: sensitive → 1.0, resistant → 0.0
    def remap_label(x, y):
        new_label = tf.cast(tf.equal(y, sensitive_idx), tf.float32)
        return x, new_label

    ds = ds.map(remap_label)

    if augment:
        augmenter = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom(0.1),
            tf.keras.layers.RandomBrightness(0.15),
            tf.keras.layers.RandomContrast(0.15),
        ])
        ds = ds.map(lambda x, y: (augmenter(x, training=True), y))

    # Normalise pixels to [0, 1] — must match preprocess_image.py
    normalise = tf.keras.layers.Rescaling(1.0 / 255)
    ds = ds.map(lambda x, y: (normalise(x), y))
    return ds.prefetch(tf.data.AUTOTUNE)


def build_model():
    """MobileNetV2 transfer-learning model for binary sensitive/resistant classification."""
    base = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet"
    )
    base.trainable = False  # Phase 1: freeze backbone

    inputs  = tf.keras.Input(shape=IMG_SIZE + (3,))
    x       = base(inputs, training=False)
    x       = tf.keras.layers.GlobalAveragePooling2D()(x)
    x       = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model   = tf.keras.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model, base


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    dataset_root = sys.argv[1]
    output_path  = sys.argv[2]

    print("Loading datasets...")
    train_ds = load_dataset(dataset_root, "train", augment=True)
    val_ds   = load_dataset(dataset_root, "valid", augment=False)

    print("Building model (MobileNetV2 transfer learning)...")
    model, base = build_model()
    model.summary()

    checkpoint_path = "best_sensitive_checkpoint.h5"
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path,
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=5,
            restore_best_weights=True,
        ),
    ]

    print(f"Phase 1: training classification head for up to {EPOCHS} epochs...")
    model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)

    print(f"Phase 2: fine-tuning top layers for up to {FINE_TUNE_EPOCHS} epochs...")
    base.trainable = True
    for layer in base.layers[:-30]:   # keep early generic features frozen
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(train_ds, validation_data=val_ds, epochs=FINE_TUNE_EPOCHS, callbacks=callbacks)

    print(f"Saving best model to {output_path}...")
    model.save(output_path)
    print("Done! Restart the FastAPI server to load the retrained model.")


if __name__ == "__main__":
    main()
