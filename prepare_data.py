import os
import random
import shutil

# Create directories for the data subset
os.makedirs('dataset_subset/images/train', exist_ok=True)
os.makedirs('dataset_subset/labels/train', exist_ok=True)

# Get a list of all image files
all_images = os.listdir('dataset/train/images')

# Randomly select 200 images
random.shuffle(all_images)
selected_images = all_images[:200]

# Copy selected images and their corresponding labels
for image_name in selected_images:
    # Copy image
    shutil.copy(f'dataset/train/images/{image_name}', f'dataset_subset/images/train/{image_name}')

    # Copy label
    label_name = os.path.splitext(image_name)[0] + '.txt'
    if os.path.exists(f'dataset/train/labels/{label_name}'):
        shutil.copy(f'dataset/train/labels/{label_name}', f'dataset_subset/labels/train/{label_name}')

print(f"Created a subset of 200 images and labels in 'dataset_subset' directory.")
