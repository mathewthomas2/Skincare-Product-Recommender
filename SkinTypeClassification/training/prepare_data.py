import os
import shutil
from sklearn.model_selection import train_test_split
import cv2
import numpy as np

def prepare_dataset():
    """Prepare and organize the dataset"""
    # Create necessary directories
    base_dirs = [
        'data/raw/oily_dry/oily',
        'data/raw/oily_dry/dry',
        'data/raw/pigmentation/pigmented',
        'data/raw/pigmentation/non_pigmented'
    ]
    
    for dir_path in base_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    print("Dataset directories created. Please organize your images into the following structure:")
    print("\ndata/raw/")
    print("├── oily_dry/")
    print("│   ├── oily/")
    print("│   └── dry/")
    print("└── pigmentation/")
    print("    ├── pigmented/")
    print("    └── non_pigmented/")
    
    print("\nAfter organizing your images, run train_models.py")

if __name__ == "__main__":
    prepare_dataset()