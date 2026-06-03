import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import json
import os

# CONFIG
DATASET_DIR = "/Users/anishagautam/Downloads/plantvillage dataset"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 20
FINE_TUNE_EPOCHS = 5
MODEL_PATH = "best_disease_model.h5"

# DATA
datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    zoom_range=0.2,
    shear_range=0.1,
    brightness_range=[0.8, 1.2],
    validation_split=0.2,
)

train_gen = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training",
)

val_gen = datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
)

num_classes = len(train_gen.class_indices)
class_names = list(train_gen.class_indices.keys())

# Save class names
with open("class_names.json", "w") as f:
    json.dump(class_names, f, indent=2)

print(f"\nFound {num_classes} classes")

# LOAD OR BUILD MODEL
if os.path.exists(MODEL_PATH):
    print("\nLoading existing model...")
    model = tf.keras.models.load_model(MODEL_PATH)
    SKIP_TRAINING = True
else:
    print("\nBuilding new model...")
    SKIP_TRAINING = False

    base_model = MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet"
    )
    base_model.trainable = False

    x = layers.GlobalAveragePooling2D()(base_model.output)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    output = layers.Dense(num_classes, activation="softmax")(x)

    model = models.Model(base_model.input, output)

# COMPILE
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

# CALLBACKS
cb = [
    callbacks.EarlyStopping(patience=6, restore_best_weights=True, verbose=1),
    callbacks.ReduceLROnPlateau(patience=3, factor=0.3, min_lr=1e-7, verbose=1),
    callbacks.ModelCheckpoint(MODEL_PATH, save_best_only=True, verbose=1),
]

# PHASE 1: TRAIN ONLY IF NEW MODEL
if not SKIP_TRAINING:
    print("\n── Phase 1: Training (frozen base) ──")
    model.fit(train_gen, validation_data=val_gen, epochs=EPOCHS, callbacks=cb)
else:
    print("\n Skipping Phase 1 (already trained)")

# PHASE 2: FINE-TUNING (FINAL FIX)
print("\n── Phase 2: Fine-tuning ──")

# Unfreeze everything
for layer in model.layers:
    layer.trainable = True

# Freeze most layers (train only last 30)
for layer in model.layers[:-30]:
    layer.trainable = False

# Recompile with low LR
model.compile(
    optimizer=tf.keras.optimizers.Adam(1e-5),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

# Train ONLY fine-tuning
model.fit(train_gen, validation_data=val_gen, epochs=FINE_TUNE_EPOCHS, callbacks=cb)

# SAVE FINAL MODEL
model.save("final_disease_model.h5")

print("\nDONE!")
print("Saved: final_disease_model.h5")
print("Saved: class_names.json")
