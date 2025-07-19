#!/usr/bin/env python3
"""
Create a simple square icon for the Trainer application.
This creates a 256x256 PNG icon with a train symbol.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_train_icon():
    # Create a new 256x256 image with a dark background
    size = 256
    img = Image.new('RGBA', (size, size), (26, 26, 26, 255))  # Dark background
    draw = ImageDraw.Draw(img)
    
    # Draw a rounded rectangle background
    margin = 20
    draw.rounded_rectangle(
        [margin, margin, size-margin, size-margin],
        radius=30,
        fill=(30, 136, 229, 255),  # Blue background
        outline=(255, 255, 255, 255),
        width=3
    )
    
    # Draw a simple train representation
    # Train body
    train_x = 60
    train_y = 100
    train_width = 136
    train_height = 60
    
    # Main train body
    draw.rectangle(
        [train_x, train_y, train_x + train_width, train_y + train_height],
        fill=(255, 255, 255, 255)
    )
    
    # Train windows
    window_size = 20
    window_y = train_y + 10
    for i in range(3):
        window_x = train_x + 15 + (i * 40)
        draw.rectangle(
            [window_x, window_y, window_x + window_size, window_y + window_size],
            fill=(30, 136, 229, 255)
        )
    
    # Train wheels
    wheel_radius = 15
    wheel_y = train_y + train_height + 5
    for i in range(4):
        wheel_x = train_x + 20 + (i * 35)
        draw.ellipse(
            [wheel_x - wheel_radius, wheel_y - wheel_radius,
             wheel_x + wheel_radius, wheel_y + wheel_radius],
            fill=(64, 64, 64, 255),
            outline=(255, 255, 255, 255),
            width=2
        )
    
    # Add text "TRAINER" at the bottom
    try:
        # Try to use a built-in font
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    text = "TRAINER"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = (size - text_width) // 2
    text_y = size - margin - text_height - 10
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the icon
    output_path = os.path.join('assets', 'trainer_icon.png')
    os.makedirs('assets', exist_ok=True)
    img.save(output_path, 'PNG')
    print(f"Icon created successfully at: {output_path}")
    print(f"Icon size: {img.size}")
    
    # Also create smaller versions for different uses
    for icon_size in [128, 64, 32, 16]:
        resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        resized_path = os.path.join('assets', f'trainer_icon_{icon_size}.png')
        resized.save(resized_path, 'PNG')
        print(f"Created {icon_size}x{icon_size} version at: {resized_path}")

if __name__ == "__main__":
    try:
        create_train_icon()
    except ImportError:
        print("Error: Pillow library is required. Install it with: pip install Pillow")
    except Exception as e:
        print(f"Error creating icon: {e}")