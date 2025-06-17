import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Flatten, Dropout
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

def create_cnn_model(input_shape=(224, 224, 3)):
    """Create a CNN model with improved architecture"""
    model = Sequential([
        # First convolution block
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape, padding='same'),
        Conv2D(32, (3, 3), activation='relu', padding='same'),
        MaxPooling2D((2, 2)),
        Dropout(0.25),
        
        # Second convolution block
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        Conv2D(64, (3, 3), activation='relu', padding='same'),
        MaxPooling2D((2, 2)),
        Dropout(0.25),
        
        # Third convolution block
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        Conv2D(128, (3, 3), activation='relu', padding='same'),
        MaxPooling2D((2, 2)),
        Dropout(0.25),
        
        # Dense layers
        Flatten(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(256, activation='relu'),
        Dropout(0.5),
        Dense(1, activation='sigmoid')
    ])
    return model

def plot_training_history(history, model_name):
    """Plot accuracy and loss curves"""
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Training Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title(f'{model_name} Training Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title(f'{model_name} Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(f'training_history_{model_name}.png')
    plt.close()

def get_class_weights(directory):
    """Calculate class weights for imbalanced dataset"""
    total_samples = 0
    class_counts = {}
    
    for class_name in os.listdir(directory):
        class_dir = os.path.join(directory, class_name)
        if os.path.isdir(class_dir):
            count = len(os.listdir(class_dir))
            class_counts[class_name] = count
            total_samples += count
    
    class_weights = {}
    for i, (class_name, count) in enumerate(class_counts.items()):
        class_weights[i] = total_samples / (len(class_counts) * count)
    
    return class_weights

def train_model(data_dir, model_name):
    """Train a model for binary classification"""
    # Data augmentation for training
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        validation_split=0.2
    )

    # Only rescaling for validation
    valid_datagen = ImageDataGenerator(
        rescale=1./255,
        validation_split=0.2
    )

    # Load and prepare the data
    train_generator = train_datagen.flow_from_directory(
        data_dir,
        target_size=(224, 224),
        batch_size=16,
        class_mode='binary',
        subset='training'
    )

    validation_generator = valid_datagen.flow_from_directory(
        data_dir,
        target_size=(224, 224),
        batch_size=16,
        class_mode='binary',
        subset='validation'
    )

    # Create and compile the model
    model = create_cnn_model()
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)  # Lower learning rate
    model.compile(
        optimizer=optimizer,
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    # Calculate class weights before model.fit
    class_weights = get_class_weights(data_dir)
    
    # Update the model.fit call
    history = model.fit(
        train_generator,
        epochs=50,
        validation_data=validation_generator,
        class_weight=class_weights,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=3,
                min_lr=0.00001
            )
        ]
    )

    # Plot training history
    plot_training_history(history, model_name)

    # Save the model
    model.save(f'app/models/{model_name}_model.h5')

    # Evaluate the model
    validation_loss, validation_accuracy = model.evaluate(validation_generator)
    print(f"\n{model_name} Model Evaluation:")
    print(f"Validation Accuracy: {validation_accuracy:.4f}")
    print(f"Validation Loss: {validation_loss:.4f}")

    return validation_accuracy


def main():
    # Create models directory if it doesn't exist
    os.makedirs('app/models', exist_ok=True)

    # Train models for different classifications
    accuracies = {}
    
    # Train Oily vs Dry model
    print("\nTraining Oily vs Dry Model...")
    accuracies['oily_dry'] = train_model('data/raw/oily_dry', 'oily_dry')

    # Train Pigmented vs Non-pigmented model
    print("\nTraining Pigmentation Model...")
    accuracies['pigmentation'] = train_model('data/raw/pigmentation', 'pigmented_nonpigmented')

    # Print overall results
    print("\nFinal Model Accuracies:")
    for model_name, accuracy in accuracies.items():
        print(f"{model_name}: {accuracy:.4f}")

if __name__ == "__main__":
    main()
