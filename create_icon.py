#!/usr/bin/env python3
"""
Convert train_emoji.ico to proper square PNG icons for the Trainer application.
"""

import os
import sys

def create_train_icon_from_ico():
    """Convert train_emoji.ico to square PNG icons of various sizes."""
    try:
        import imageio.v3 as iio
    except ImportError:
        print("Error: imageio library is required. Install it with: pip install imageio")
        return False
    
    ico_path = os.path.join('assets', 'train_emoji.ico')
    if not os.path.exists(ico_path):
        print(f"Error: {ico_path} not found!")
        return False
    
    try:
        # Read the ICO file
        print(f"Reading {ico_path}...")
        ico_data = iio.imread(ico_path)
        
        # Handle multi-frame ICO files
        if hasattr(ico_data, '__len__') and len(ico_data.shape) > 2:
            # If it's a multi-frame ICO, use the first frame
            if len(ico_data.shape) == 4:  # Multiple frames
                img = ico_data[0]
            else:
                img = ico_data
        else:
            img = ico_data
        
        print(f"Original image shape: {img.shape}")
        
        # Import PIL for image processing
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            print("Error: Pillow library is required. Install it with: pip install Pillow")
            return False
        
        # Convert to PIL Image
        if img.dtype != np.uint8:
            img = (img * 255).astype(np.uint8)
        
        pil_img = Image.fromarray(img)
        
        # Ensure it's square by cropping or padding if needed
        width, height = pil_img.size
        if width != height:
            # Make it square by taking the smaller dimension
            size = min(width, height)
            # Center crop
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            pil_img = pil_img.crop((left, top, right, bottom))
            print(f"Cropped to square: {size}x{size}")
        
        # Create the main 256x256 icon
        main_icon = pil_img.resize((256, 256), Image.Resampling.LANCZOS)
        output_path = os.path.join('assets', 'trainer_icon.png')
        main_icon.save(output_path, 'PNG')
        print(f"Created main icon: {output_path} (256x256)")
        
        # Create smaller versions
        sizes = [128, 64, 32, 16]
        for size in sizes:
            resized = pil_img.resize((size, size), Image.Resampling.LANCZOS)
            resized_path = os.path.join('assets', f'trainer_icon_{size}.png')
            resized.save(resized_path, 'PNG')
            print(f"Created {size}x{size} icon: {resized_path}")
        
        print("\nAll icons created successfully!")
        return True
        
    except Exception as e:
        print(f"Error processing icon: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_train_icon_from_ico()
    sys.exit(0 if success else 1)