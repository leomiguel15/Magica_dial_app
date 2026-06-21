from PIL import Image
import os

# Get current script directory
base_path = os.path.dirname(os.path.abspath(__file__))

# PNG input path
png_path = os.path.join(base_path, "images", "icon.png")

# ICO output path
ico_path = os.path.join(base_path, "images", "icon.ico")

try:
    # Open image
    img = Image.open(png_path)

    # Convert to RGBA (important)
    img = img.convert("RGBA")

    # Save as ICO with multiple sizes
    img.save(
        ico_path,
        format="ICO",
        sizes=[
            (16, 16),
            (32, 32),
            (48, 48),
            (64, 64),
            (128, 128),
            (256, 256)
        ]
    )

    print(f"SUCCESS: ICO file created at:\n{ico_path}")

except Exception as e:
    print("ERROR:")
    print(e)