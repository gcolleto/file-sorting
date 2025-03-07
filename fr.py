import os
import sys
from datetime import datetime
from PIL import Image

# Define common image file extensions (case-insensitive)
image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']

def is_image(file_path):
    """
    Check if a file is an image based on its extension.
    
    Args:
        file_path (str): Full path to the file.
    
    Returns:
        bool: True if the file is an image, False otherwise.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in image_extensions

def get_exif_date(file_path):
    """
    Extract the date taken from an image's EXIF data.
    
    Args:
        file_path (str): Full path to the image file.
    
    Returns:
        str or None: Date in YYYYMMDD_HHmmss format, or None if unavailable.
    """
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if exif_data and 36867 in exif_data:  # 36867 is DateTimeOriginal tag
                date_str = exif_data[36867]  # Format: "YYYY:MM:DD HH:MM:SS"
                dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                return dt.strftime("%Y%m%d_%H%M%S")
    except Exception as e:
        print(f"Error getting EXIF data for {file_path}: {e}")
    return None

def get_modification_date(file_path):
    """
    Get the modification date of a file as a fallback.
    
    Args:
        file_path (str): Full path to the file.
    
    Returns:
        str: Date in YYYYMMDD_HHmmss format.
    """
    mtime = os.path.getmtime(file_path)  # Returns seconds since epoch
    dt = datetime.fromtimestamp(mtime)   # Converts to local time
    return dt.strftime("%Y%m%d_%H%M%S")

def get_file_date(file_path):
    """
    Determine the appropriate date for an image file.
    
    Args:
        file_path (str): Full path to the image file.
    
    Returns:
        str: Date in YYYYMMDD_HHmmss format.
    """
    date = get_exif_date(file_path)
    if date:
        return date
    return get_modification_date(file_path)

def rename_files_in_folder(folder_path):
    """
    Rename all image files in the specified folder to the format img_X_Y.Z.
    
    Args:
        folder_path (str): Path to the folder containing files to rename.
    """
    # Check if the folder exists and is a directory
    if not os.path.isdir(folder_path):
        print(f"{folder_path} is not a directory.")
        sys.exit(1)

    # Process each file in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Skip if it's not a file (e.g., directories)
        if not os.path.isfile(file_path):
            continue
        
        # Skip if it's not an image
        if not is_image(file_path):
            continue
        
        # Get the date for the image file
        date = get_file_date(file_path)
        if date is None:
            print(f"Could not determine date for {filename}, skipping.")
            continue
        
        # Extract the original file extension
        _, ext = os.path.splitext(filename)
        
        # Start with Y = 0 and find a unique filename
        y = 0
        while True:
            new_name = f"img_{date}_{y}{ext}"
            new_path = os.path.join(folder_path, new_name)
            if not os.path.exists(new_path):
                break
            y += 1
        
        # Rename the file
        try:
            os.rename(file_path, new_path)
            print(f"Renamed {filename} to {new_name}")
        except Exception as e:
            print(f"Error renaming {filename} to {new_name}: {e}")

if __name__ == "__main__":
    # Check for command-line argument
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path>")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    rename_files_in_folder(folder_path)

