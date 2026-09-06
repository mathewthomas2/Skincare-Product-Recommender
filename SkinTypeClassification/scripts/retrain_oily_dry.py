import sys
import tensorflow as tf
 
IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 10
FINE_TUNE_EPOCHS = 10
 
 
def load_dataset(root_dir, split, augment=False):
    # Let TF auto-detect all subfolders present (dry, normal, oily - alphabetical order).
    # We then drop "normal" and remap to a clean binary 0/1 (dry/oily) label.
    ds = tf.keras.utils.image_dataset_from_directory(
        f"{root_dir}/{split}",
        labels="inferred",
        label_mode="int",
        image_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        shuffle=(split == "train"),
    )
    class_names = ds.class_names  # e.g. ['dry', 'normal', 'oily']
    print(f"  [{split}] detected classes (index order): {class_names}")
    dry_idx = class_names.index("dry")
    oily_idx = class_names.index("oily")
 
    # Drop any "normal" (or other) images - keep only dry/oily
    ds = ds.unbatch()
    ds = ds.filter(lambda x, y: tf.reduce_any(tf.equal(y, [dry_idx, oily_idx])))
 
    # Remap: dry_idx -> 0.0, oily_idx -> 1.0
    def remap_label(x, y):
        new_label = tf.cast(tf.equal(y, oily_idx), tf.float32)
        return x, new_label
 
    ds = ds.map(remap_label)
    ds = ds.batch(BATCH_SIZE)
 
    if augment:
        augmenter = tf.keras.Sequential([
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom(0.1),
            tf.keras.layers.RandomBrightness(0.15),
            tf.keras.layers.RandomContrast(0.15),
        ])
        ds = ds.map(lambda x, y: (augmenter(x, training=True), y))
 
    # Rescale pixels to [0,1] to match preprocess_image.py's normalization
    normalization_layer = tf.keras.layers.Rescaling(1.0 / 255)
    ds = ds.map(lambda x, y: (normalization_layer(x), y))
    return ds.prefetch(tf.data.AUTOTUNE)
 
 
def build_model():
    base = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet"
    )
    base.trainable = False  # freeze pretrained feature extractor for phase 1
 
    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = base(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model = tf.keras.Model(inputs, outputs)
 
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model, base
 
 
def main():
    if len(sys.argv) < 3:
        print("Usage: python retrain_oily_dry.py path/to/dataset/root path/to/output_model.h5")
        sys.exit(1)
 
    dataset_root = sys.argv[1]
    output_path = sys.argv[2]
 
    print("Loading datasets...")
    train_ds = load_dataset(dataset_root, "train", augment=True)
    val_ds = load_dataset(dataset_root, "valid", augment=False)
 
    print("Building model (MobileNetV2 transfer learning)...")
    model, base = build_model()
    model.summary()
 
    checkpoint_path = "best_checkpoint.h5"
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path, monitor="val_accuracy", save_best_only=True, verbose=1
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=5, restore_best_weights=True
        ),
    ]
 
    print(f"Phase 1: training head only for up to {EPOCHS} epochs...")
    model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)
 
    print(f"Phase 2: fine-tuning top layers of MobileNetV2 for up to {FINE_TUNE_EPOCHS} epochs...")
    base.trainable = True
    # Only unfreeze the last ~30 layers - keep early generic features frozen
    for layer in base.layers[:-30]:
        layer.trainable = False
 
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),  # much lower LR for fine-tuning
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(train_ds, validation_data=val_ds, epochs=FINE_TUNE_EPOCHS, callbacks=callbacks)
 
    # model now holds the best weights seen across both phases (restore_best_weights=True)
    print(f"Saving best model to {output_path}...")
    model.save(output_path)
    print("Done. Restart your FastAPI server to load the new model.")
 
 
if __name__ == "__main__":
    main()
