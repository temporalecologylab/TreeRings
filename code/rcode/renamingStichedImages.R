# Set the main directory path (adjust this to your actual main directory location)
main_directory <- "/Volumes/PortableSSD/cookies"

# Get all .tif files in the directory and subdirectories
all_files <- dir_ls(main_directory, recurse = TRUE, glob = "*.tif")

# Loop through each file!
for (file in all_files) {
  
  # Grab the path of the folder one level up from the .tif file
  parent_folder_path <- path_dir(path_dir(file))
  
  # Extract the folder name to use as the ID
  folder_id <- path_file(parent_folder_path)
  
  # Construct the new file name by combining the folder ID with "-30per.tif"
  new_file_name <- paste0(folder_id, "-30per.tif")
  
  # Create the full path for the new file name
  new_file_path <- path(path_dir(file), new_file_name)
  
  # Rename the file
  file_move(file, new_file_path)
  
  # Print the old and new file paths for confirmation
  message("Renamed ", file, " to ", new_file_path)
}
