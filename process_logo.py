from PIL import Image

def process_logo():
    # Open the image
    img = Image.open('logo.jpeg')
    
    # Convert to RGBA
    img = img.convert("RGBA")
    
    datas = img.getdata()
    
    newData = []
    for item in datas:
        # Change all white (also shades of whites)
        # to transparent
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
            
    img.putdata(newData)
    
    # Get the bounding box of the non-transparent area
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # Save the processed image for the frontend
    img.save('frontend/public/logo.png', 'PNG')
    
    # Create favicon
    # Favicon typically expects an ICO file, we can also use a small PNG
    # First, let's make it square for favicon
    width, height = img.size
    size = max(width, height)
    square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    square_img.paste(img, ((size - width) // 2, (size - height) // 2))
    
    # Resize for favicon
    favicon = square_img.resize((32, 32), Image.Resampling.LANCZOS)
    favicon.save('frontend/public/favicon.ico', format='ICO', sizes=[(32, 32)])
    favicon.save('frontend/public/favicon.png', 'PNG')

    print("Successfully processed logo and created favicon.")

if __name__ == "__main__":
    process_logo()