import numpy as np
import tensorflow as tf
from skimage import transform


def preprocess_image(image_path: str, img_width: int = 224, img_height: int = 224) -> np.ndarray:
    """
    Preprocesses an image for skin type prediction.

    Args:
        image_path (str): Path to the input image.
        img_width  (int): Target width in pixels (default 224).
        img_height (int): Target height in pixels (default 224).

    Returns:
        np.ndarray: Shape (1, img_height, img_width, 3), pixels normalised to [0, 1].
    """
    image = tf.keras.utils.load_img(image_path)
    input_arr = tf.keras.utils.img_to_array(image)

    # Resize to the model's expected spatial dimensions
    resized = transform.resize(input_arr, (img_height, img_width, 3))

    # Normalise to [0, 1] — skimage.transform.resize already outputs float64
    # values in [0, 1] when the source is uint8, but we guard explicitly.
    if resized.max() > 1.0:
        resized = resized / 255.0

    return np.array([resized], dtype=np.float32)
