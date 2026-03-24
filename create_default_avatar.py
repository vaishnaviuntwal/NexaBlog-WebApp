from PIL import Image, ImageDraw
import os

def create_default_avatar():
    # Create directories if they don't exist
    os.makedirs('static/profile_pics', exist_ok=True)
    os.makedirs('static/post_pics', exist_ok=True)
    
    # Create a 200x200 image with a blue background
    img = Image.new('RGB', (200, 200), color='#6366f1')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple user icon
    draw.ellipse([50, 50, 150, 150], fill='white')  # Head
    draw.ellipse([75, 75, 125, 125], fill='#6366f1')  # Face area
    
    # Save as default.png
    img.save('static/profile_pics/default.png', 'PNG')
    print("✅ Default avatar created successfully!")
    print("✅ Directories created: static/profile_pics/, static/post_pics/")

if __name__ == '__main__':
    create_default_avatar()