import os
import shutil
from datetime import datetime
import re
from math import radians, cos, sin, asin, sqrt
import argparse
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

def format_size(size):
    if size < 1024:
        return f"{size} bytes"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


# Function to calculate distance between two GPS coordinates (Haversine formula)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

# Function to extract EXIF data from an image
def get_exif_data(image_path):
    try:
        image = Image.open(image_path)
        info = image._getexif()
        exif_data = {}
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    exif_data[decoded] = gps_data
                else:
                    exif_data[decoded] = value
        return exif_data
    except Exception:
        return {}

# Function to extract GPS coordinates from EXIF data
def get_gps_info(image_path):
    exif_data = get_exif_data(image_path)
    if 'GPSInfo' in exif_data:
        gps_info = exif_data['GPSInfo']
        if all(k in gps_info for k in ['GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude', 'GPSLongitudeRef']):
            lat = gps_info['GPSLatitude'][0] + gps_info['GPSLatitude'][1] / 60 + gps_info['GPSLatitude'][2] / 3600
            if gps_info['GPSLatitudeRef'] == 'S':
                lat = -lat
            lon = gps_info['GPSLongitude'][0] + gps_info['GPSLongitude'][1] / 60 + gps_info['GPSLongitude'][2] / 3600
            if gps_info['GPSLongitudeRef'] == 'W':
                lon = -lon
            return (lat, lon)
    return None

# Function to get city name from GPS coordinates
def get_city_from_coords(lat, lon):
    geolocator = Nominatim(user_agent="image_organizer_script")
    try:
        location = geolocator.reverse((lat, lon), language='en')
        if location and 'address' in location.raw:
            address = location.raw['address']
            return address.get('city') or address.get('town') or address.get('village') or 'Unknown'
        return 'Unknown'
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding failed for ({lat}, {lon}): {e}")
        return 'Unknown'

# Function to identify duplicates based on prefix and size
def identify_duplicates(folder_path, image_files):
    prefix_size_to_files = {}
    for file in image_files:
        match = re.match(r'(img_\d{8}_\d{6})_\d+\.\w+', file)
        if match:
            prefix = match.group(1)
            file_path = os.path.join(folder_path, file)
            try:
                size = os.path.getsize(file_path)
                key = (prefix, size)
                if key not in prefix_size_to_files:
                    prefix_size_to_files[key] = []
                prefix_size_to_files[key].append(file)
            except OSError:
                print(f"Cannot access {file_path}")
                continue
    
    files_to_remove = set()
    for (prefix, size), files in prefix_size_to_files.items():
        if len(files) > 1:
            # Keep the first file, mark others for removal
            for file in files[1:]:
                files_to_remove.add(file)
    return files_to_remove

# Function to sanitize folder names
def sanitize_folder_name(name):
    return re.sub(r'[^\w\-]', '_', name)

# Main script
def organize_images(folder_path, dry_run=False):
    threshold = 50  # Distance threshold in kilometers for same location

    # List image files
    image_files = [f for f in os.listdir(folder_path) if re.match(r'img_\d{8}_\d{6}_\d+\.\w+', f)]
    
    # Identify duplicates
    files_to_remove = identify_duplicates(folder_path, image_files)
    
    # Compute total freed memory
    total_memory_freed = 0
    for file in files_to_remove:
        file_path = os.path.join(folder_path, file)
        try:
            total_memory_freed += os.path.getsize(file_path)
        except OSError:
            print(f"Cannot access {file_path}")

    if dry_run:
        if files_to_remove:
            print("Would remove the following duplicate files:")
            for file in files_to_remove:
                print(f"  {file} {format_size(os.path.getsize(os.path.join(folder_path, file)))}")
        files_to_process = [f for f in image_files if f not in files_to_remove]
    else:
        for file in files_to_remove:
            file_path = os.path.join(folder_path, file)
            try:
                os.remove(file_path)
                print(f"Removed duplicate file: {file}")
            except OSError as e:
                print(f"Error removing {file_path}: {e}")
        files_to_process = [f for f in image_files if f not in files_to_remove]
    
    # Extract date, GPS, and location for each file
    pictures = []
    for file in files_to_process:
        match = re.match(r'img_(\d{8}_\d{6})_\d+\.\w+', file)
        if match:
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                gps = get_gps_info(os.path.join(folder_path, file))
                if gps:
                    lat, lon = gps
                    location = get_city_from_coords(lat, lon)
                else:
                    location = "Unknown"
                pictures.append({'filename': file, 'date': date_obj, 'gps': gps, 'location': location})
            except ValueError:
                print(f"Skipping file with invalid date: {file}")
                continue
    
    # Group pictures by year
    pictures_by_year = {}
    for pic in pictures:
        year = pic['date'].year
        if year not in pictures_by_year:
            pictures_by_year[year] = []
        pictures_by_year[year].append(pic)
    
    # Process each year
    for year, pics in pictures_by_year.items():
        # Sort by date
        pics.sort(key=lambda x: x['date'])
        
        # Group into trips
        trips = []
        if pics:
            current_trip = [pics[0]]
            for i in range(1, len(pics)):
                prev_pic = pics[i - 1]
                curr_pic = pics[i]
                date_diff = (curr_pic['date'].date() - prev_pic['date'].date()).days
                same_location = (
                    (prev_pic['gps'] is not None and curr_pic['gps'] is not None and
                     haversine(prev_pic['gps'][0], prev_pic['gps'][1], curr_pic['gps'][0], curr_pic['gps'][1]) < threshold)
                    or
                    (prev_pic['gps'] is None and curr_pic['gps'] is None and
                     prev_pic['location'] == curr_pic['location'])
                )
                if (date_diff == 0 or date_diff == 1) and same_location:
                    current_trip.append(curr_pic)
                else:
                    trips.append(current_trip)
                    current_trip = [curr_pic]
            trips.append(current_trip)
        
        # Assign folder names and move files
        name_dict = {}
        for trip in trips:
            starting_date = trip[0]['date']
            YYYY = starting_date.year
            MM = f"{starting_date.month:02d}"
            LOCATION = sanitize_folder_name(trip[0]['location'])
            
            base_name = f"{YYYY}_{MM}_{LOCATION}"
            if base_name not in name_dict:
                folder_name = base_name
                name_dict[base_name] = 0
            else:
                X = name_dict[base_name]
                folder_name = f"{base_name}_{X}"
                name_dict[base_name] += 1
            
            year_folder = os.path.join(folder_path, str(year))
            trip_folder = os.path.join(year_folder, folder_name)
            
            if dry_run:
                print(f"Would create folder: {trip_folder}")
                for pic in trip:
                    print(f"Would move {pic['filename']} to {trip_folder}")
            else:
                os.makedirs(trip_folder, exist_ok=True)
                for pic in trip:
                    src = os.path.join(folder_path, pic['filename'])
                    dst = os.path.join(trip_folder, pic['filename'])
                    shutil.move(src, dst)
                    print(f"Moved {pic['filename']} to {trip_folder}")

    if total_memory_freed > 0:
        if dry_run:
            print(f"Would free {format_size(total_memory_freed)}")
        else:
            print(f"Freed {format_size(total_memory_freed)}")

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Organize images into folders based on date and location, with duplicate removal.')
    parser.add_argument('folder_path', help='Path to the folder containing the images')
    parser.add_argument('--dry-run', action='store_true', help='Simulate the actions without modifying the file system')
    args = parser.parse_args()

    organize_images(args.folder_path, dry_run=args.dry_run)
