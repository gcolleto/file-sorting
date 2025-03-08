import os
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re
from math import radians, cos, sin, asin, sqrt
import argparse
from geopy.geocoders import Nominatim  # Added for reverse geocoding
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable  # Handle geocoding errors

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
            lat = [x for x in gps_info['GPSLatitude']]  #[float(x[0]) / float(x[1]) if x[1] != 0 else 0 for x in gps_info['GPSLatitude']]
            lat = lat[0] + lat[1] / 60 + lat[2] / 3600
            if gps_info['GPSLatitudeRef'] == 'S':
                lat = -lat
            #lon = [float(x[0]) / float(x[1]) if x[1] != 0 else 0 for x in gps_info['GPSLongitude']]
            lon = [x for x in gps_info['GPSLongitude']]  #[float(x[0]) / float(x[1]) if x[1] != 0 else 0 for x in gps_info['GPSLatitude']]
            lon = lon[0] + lon[1] / 60 + lon[2] / 3600
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
        return f'Unknown_{lat}_{lon}'
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding failed for ({lat}, {lon}): {e}")
        return f'Unknown_{lat}_{lon}'


# Main script
def organize_images(folder_path, dry_run=False):
    threshold = 50  # Distance threshold in kilometers for same location
    total_files = 0
    total_folders = 0

    # List files matching the pattern 'img_YYYYMMDD_HHmmss_X.Y'
    files = [f for f in os.listdir(folder_path) if re.match(r'img_\d{8}_\d{6}_\d+\.\w+', f)]

    # Extract date and GPS for each file
    pictures = []
    for file in files:
        match = re.match(r'img_(\d{8}_\d{6})_\d+\.\w+', file)
        if match:
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                gps = get_gps_info(os.path.join(folder_path, file))
                pictures.append({'filename': file, 'date': date_obj, 'gps': gps})
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
        # Sort pictures by date
        pics.sort(key=lambda x: x['date'])

        # Group into trips/sequences
        trips = []
        if pics:
            current_trip = [pics[0]]
            for i in range(1, len(pics)):
                prev_pic = pics[i - 1]
                curr_pic = pics[i]
                date_diff = (curr_pic['date'].date() - prev_pic['date'].date()).days
                same_location = (
                    (prev_pic['gps'] is None and curr_pic['gps'] is None) or
                    (prev_pic['gps'] is not None and curr_pic['gps'] is not None and
                     haversine(prev_pic['gps'][0], prev_pic['gps'][1], curr_pic['gps'][0], curr_pic['gps'][1]) < threshold)
                )
                if (date_diff == 0 or date_diff == 1) and same_location:
                    current_trip.append(curr_pic)
                else:
                    trips.append(current_trip)
                    current_trip = [curr_pic]
            trips.append(current_trip)

        # Assign folder names and simulate or perform actions
        name_dict = {}  # Tracks the next X for each base_name
        for trip in trips:
            starting_date = trip[0]['date']
            YYYY = starting_date.year
            MM = f"{starting_date.month:02d}"
            if trip[0]['gps'] is not None:
                lat, lon = trip[0]['gps']
                # Get city name instead of coordinates
                LOCATION = get_city_from_coords(lat, lon)
            else:
                LOCATION = 'Unknown'

            base_name = f"{YYYY}_{MM}_{LOCATION}"
            if base_name not in name_dict:
                folder_name = base_name
                name_dict[base_name] = 0
            else:
                X = name_dict[base_name]
                folder_name = f"{base_name}_{X}"
                name_dict[base_name] += 1

            # Define folder paths
            year_folder = os.path.join(folder_path, str(year))
            trip_folder = os.path.join(year_folder, folder_name)

            # Dry run: print what would be done
            if dry_run:
                total_folders += 1
                print(f"Would create folder: {trip_folder}")
                for pic in trip:
                    total_files += 1
                    src = os.path.join(folder_path, pic['filename'])
                    dst = os.path.join(trip_folder, pic['filename'])
                    print(f"Would move {pic['filename']} to {trip_folder}")
            else:
                # Actually create folders and move files
                os.makedirs(trip_folder, exist_ok=True)
                for pic in trip:
                    src = os.path.join(folder_path, pic['filename'])
                    dst = os.path.join(trip_folder, pic['filename'])
                    shutil.move(src, dst)
                    print(f"Moved {pic['filename']} to {trip_folder}")

    # Summary for dry run
    if dry_run:
        print(f"\nDry run complete: Would create {total_folders} folders and move {total_files} files.")

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Organize images into folders based on date and city.')
    parser.add_argument('folder_path', help='Path to the folder containing the images')
    parser.add_argument('--dry-run', action='store_true', help='Simulate the actions without modifying the file system')
    args = parser.parse_args()

    organize_images(args.folder_path, dry_run=args.dry_run)
