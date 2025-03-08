# File sorting utilities
## Forewords 
Just a bunch of scripts to handle and sort all the files I have here and there, mostly pictures. 

- `fr.py`: rename all image file to `img_<DATE>_<ID>.<EXT>` where:
  - `<DATE>`is the date the picture was taken in format `YYYYMMDD_HHmmss`
  - `<ID>` is a counter to handle potential conflicts
  - `<EXT>` is the original extension of the file

- `fc.py`: more advanced file sorting script which will go through all the files in a folder and try to group pictures in folders based on location/temporal closeness. Files must follow the naming convention enforced by `fr.py`.

## Usage
The two scripts can be used the same way and need the target folder as input argument:
```
$> python <script> <folder> [--dry-run]
```

Optionally, a `--dry-run` flag can be passed where the script will only summarize the actions it would take but won´t actually touch the filesystem. Useful for testing. 

