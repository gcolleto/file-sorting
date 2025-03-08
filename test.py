import sys

from PIL import Image
from PIL import ExifTags



i = sys.argv[1]
print(i)


img_exif = Image.open(i).getexif()

IFD_CODE_LOOKUP = {i.value: i.name for i in ExifTags.IFD}

for tag_code, value in img_exif.items():

    # if the tag is an IFD block, nest into it
    if tag_code in IFD_CODE_LOOKUP:

        ifd_tag_name = IFD_CODE_LOOKUP[tag_code]
        print(f"IFD '{ifd_tag_name}' (code {tag_code}):")
        ifd_data = img_exif.get_ifd(tag_code).items()

        for nested_key, nested_value in ifd_data:

            nested_tag_name = ExifTags.GPSTAGS.get(nested_key, None) or ExifTags.TAGS.get(nested_key, None) or nested_key
            print(f"  {nested_tag_name}: {nested_value}")

    else:

        # root-level tag
        print(f"{ExifTags.TAGS.get(tag_code)}: {value}")
