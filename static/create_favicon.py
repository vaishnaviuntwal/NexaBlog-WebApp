# create_favicon.py
from PIL import Image, ImageDraw
import os

def create_favicon():
    # Create directories if they don't exist
    os.makedirs('static', exist_ok=True)
    
    # Create a 32x32 favicon
    img = Image.new('RGB', (32, 32), color='#6366f1')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple rocket icon
    draw.rectangle([12, 8, 20, 20], fill='white')  # Rocket body
    draw.polygon([(12, 8), (16, 4), (20, 8)], fill='#f59e0b')  # Rocket tip
    draw.polygon([(12, 20), (12, 24), (16, 22), (20, 24), (20, 20)], fill='#8b5cf6')  # Rocket fins
    
    # Save as favicon
    img.save('static/favicon.ico', 'ICO')
    print("✅ Favicon created successfully!")
    print("📍 Saved as: static/favicon.ico")

def create_default_avatar():
    # Create directories if they don't exist
    os.makedirs('static/profile_pics', exist_ok=True)
    os.makedirs('static/post_pics', exist_ok=True)
    
    # Create a 200x200 default avatar
    img = Image.new('RGB', (200, 200), color='#6366f1')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple user icon
    draw.ellipse([50, 50, 150, 150], fill='white')  # Head
    draw.ellipse([75, 75, 125, 125], fill='#6366f1')  # Face area
    
    # Save as default.png
    img.save('static/profile_pics/default.png', 'PNG')
    print("✅ Default avatar created successfully!")
    print("📍 Saved as: static/profile_pics/default.png")

if __name__ == '__main__':
    print("🚀 Creating NexaBlog assets...")
    create_favicon()
    create_default_avatar()
    print("🎉 All assets created successfully!")
    print("📁 Project structure is now ready.")