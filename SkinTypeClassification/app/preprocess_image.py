import tensorflow as tf
from skimage import transform
import numpy as np

def preprocess_image(image_path, img_width=224, img_height=224):
    """
    Preprocesses an image for skin type prediction.
    """
    image = tf.keras.utils.load_img(image_path)
    input_arr = tf.keras.utils.img_to_array(image)
    
    print(f"Original image range: [{np.min(input_arr)}, {np.max(input_arr)}]")
    
    transformed_arr = transform.resize(input_arr, (img_width, img_height, 3))
    print(f"After resize range: [{np.min(transformed_arr)}, {np.max(transformed_arr)}]")
    
    if np.max(transformed_arr) > 1.0:
        transformed_arr = transformed_arr / 255.0
        
    normalized_arr = (transformed_arr * 2.0) - 1.0
    print(f"Final normalized range: [{np.min(normalized_arr)}, {np.max(normalized_arr)}]")
    
    output_arr = np.array([normalized_arr])
    
    return output_arr
