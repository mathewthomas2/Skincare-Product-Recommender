"""
train_efficientnet_oily_dry.py — EfficientNetB0 Transfer Learning with Squeeze-and-Excitation Attention.

Why EfficientNetB0:
- Squeeze-and-Excitation (SE) blocks explicitly recalibrate channel features, capturing subtle specular highlights, pore texture, and skin sheen.
- Built-in preprocessing handles image scaling properly.
- Significantly higher representational capacity for fine skin texture classification.
"""

import os
import sys
import json
import numpy as np
import tensorflow as tf

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
PHASE_1_EPOCHS = 12
PHASE_2_EPOCHS = 15


def load_dataset(root_dir, split, augment=False):
    split_dir = os.path.join(root_dir, split)
    ds = tf.keras.utils.image_dataset_from_directory(
        split_dir,
        labels="inferred",
        label_mode="int",
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=(split == "train"),
    )
    class_names = ds.class_names
    print(f"  [{split}] Classes: {class_names}")

    dry_idx = class_names.index("dry")
    oily_idx = class_names.index("oily")

    ds = ds.unbatch()
    ds = ds.filter(lambda x, y: tf.reduce_any(tf.equal(y, [dry_idx, oily_idx])))

    def remap_label(x, y):
        new_label = tf.cast(tf.equal(y, oily_idx), tf.float32)
        return x, new_label

    ds = ds.map(remap_label)
    ds = ds.batch(BATCH_SIZE)

    if augment:
        augmenter = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.15),
            tf.keras.layers.RandomZoom(0.15),
            tf.keras.layers.RandomBrightness(0.25),
            tf.keras.layers.RandomContrast(0.25),
        ], name="data_augmentation")
        ds = ds.map(lambda x, y: (augmenter(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE)

    # EfficientNet expects [0, 255] float inputs
    ds = ds.map(lambda x, y: (tf.keras.applications.efficientnet.preprocess_input(x), y), num_parallel_calls=tf.data.AUTOTUNE)
    return ds.prefetch(tf.data.AUTOTUNE)


def compute_class_weights(root_dir):
    train_dir = os.path.join(root_dir, "train")
    dry_count = len([f for f in os.listdir(os.path.join(train_dir, "dry")) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    oily_count = len([f for f in os.listdir(os.path.join(train_dir, "oily")) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    total = dry_count + oily_count

    weight_dry = total / (2.0 * dry_count)
    weight_oily = total / (2.0 * oily_count)
    class_weights = {0: float(weight_dry), 1: float(weight_oily)}
    print(f"Class Weights — Dry (0): {weight_dry:.3f}, Oily (1): {weight_oily:.3f}")
    return class_weights


def build_model():
    base = tf.keras.applications.EfficientNetB0(
        input_shape=IMG_SIZE + (3,),
        include_top=False,
        weights="imagenet"
    )
    base.trainable = False

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = base(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(256, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)

    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=3e-4),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )
    return model, base


def find_optimal_threshold(model, val_ds):
    y_true = []
    y_pred = []
    for images, labels in val_ds:
        preds = model.predict(images, verbose=0)
        y_true.extend(labels.numpy().flatten())
        y_pred.extend(preds.flatten())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    best_thresh = 0.5
    best_balanced_acc = 0.0

    for t in np.linspace(0.1, 0.9, 81):
        preds_binary = (y_pred >= t).astype(int)
        acc_dry = np.mean(preds_binary[y_true == 0] == 0) if np.sum(y_true == 0) > 0 else 0
        acc_oily = np.mean(preds_binary[y_true == 1] == 1) if np.sum(y_true == 1) > 0 else 0
        balanced_acc = (acc_dry + acc_oily) / 2.0

        if balanced_acc > best_balanced_acc:
            best_balanced_acc = balanced_acc
            best_thresh = t

    print(f"Optimal Threshold: {best_thresh:.3f} (Val Balanced Accuracy: {best_balanced_acc*100:.2f}%)")
    return float(best_thresh)


def evaluate_test_set(model, test_ds, threshold):
    y_true = []
    y_pred = []
    for images, labels in test_ds:
        preds = model.predict(images, verbose=0)
        y_true.extend(labels.numpy().flatten())
        y_pred.extend(preds.flatten())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    preds_binary = (y_pred >= threshold).astype(int)

    acc = np.mean(preds_binary == y_true)
    dry_acc = np.mean(preds_binary[y_true == 0] == 0)
    oily_acc = np.mean(preds_binary[y_true == 1] == 1)
    dry_correct = int(np.sum(preds_binary[y_true == 0] == 0))
    dry_total = int(np.sum(y_true == 0))
    oily_correct = int(np.sum(preds_binary[y_true == 1] == 1))
    oily_total = int(np.sum(y_true == 1))
    total_correct = dry_correct + oily_correct
    total_samples = len(y_true)

    print(f"\n================ TEST SET EVALUATION ================")
    print(f"Overall Accuracy: {acc*100:.2f}% ({total_correct}/{total_samples})")
    print(f"Dry Skin Accuracy: {dry_acc*100:.2f}% ({dry_correct}/{dry_total})")
    print(f"Oily Skin Accuracy: {oily_acc*100:.2f}% ({oily_correct}/{oily_total})")
    print(f"======================================================")
    return acc, dry_acc, oily_acc


def main():
    dataset_root = "archive/Oily-Dry-Skin-Types"
    output_path = "app/models/oily_dry_model.h5"
    config_path = "app/models/model_config.json"

    print("Loading datasets with EfficientNet preprocessing...")
    train_ds = load_dataset(dataset_root, "train", augment=True)
    val_ds = load_dataset(dataset_root, "valid", augment=False)
    test_ds = load_dataset(dataset_root, "test", augment=False)

    class_weights = compute_class_weights(dataset_root)

    print("\nBuilding EfficientNetB0 Model...")
    model, base = build_model()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6, verbose=1),
    ]

    print(f"\n=== Phase 1: Training Classification Head ({PHASE_1_EPOCHS} epochs) ===")
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=PHASE_1_EPOCHS,
        class_weight=class_weights,
        callbacks=callbacks,
    )

    print(f"\n=== Phase 2: Fine-Tuning EfficientNetB0 Layers ({PHASE_2_EPOCHS} epochs) ===")
    base.trainable = True
    for layer in base.layers[:-50]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=3e-5),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )

    callbacks_p2 = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-7, verbose=1),
    ]

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=PHASE_2_EPOCHS,
        class_weight=class_weights,
        callbacks=callbacks_p2,
    )

    # Compute optimal threshold
    optimal_threshold = find_optimal_threshold(model, val_ds)

    # Evaluate on test set
    test_acc, dry_acc, oily_acc = evaluate_test_set(model, test_ds, optimal_threshold)

    # Save final model
    print(f"\nSaving model to '{output_path}'...")
    model.save(output_path)

    config = {
        "model_architecture": "EfficientNetB0",
        "oily_threshold": optimal_threshold,
        "test_accuracy": round(float(test_acc), 4),
        "dry_accuracy": round(float(dry_acc), 4),
        "oily_accuracy": round(float(oily_acc), 4),
        "sensitive_threshold": 0.3,
        "pigmented_threshold": 0.2
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Saved config: {config}")


if __name__ == "__main__":
    main()
