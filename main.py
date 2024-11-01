import requests
import re
import os
import shutil
import zipfile

# Function to get URLs from a text file
def get_urls_from_file(file_path):
    with open(file_path, 'r') as file:
        urls = file.read().splitlines()
    return urls

# Function to extract mapset ID from various URL formats
def extract_mapset_id(url):
    # Remove anything after '#' if it exists
    url = url.split('#')[0]
    
    if "beatmapsets" in url:
        return url.split('/')[-1]  # Get ID from beatmapset URL
    elif "s" in url:
        return url.split('/')[-1]  # Handle standard mapset URLs
    return None  # If the format is not recognized, return None

# Function to get mapset metadata using mapset ID
def get_mapset_metadata(mapset_id):
    map_url = f"https://catboy.best/api/v2/s/{mapset_id}"
    response = requests.get(map_url)
    response.raise_for_status()  # Check for HTTP errors
    return response.json()  # Return mapset metadata

# Modify .osu files in the downloaded .osz
def modify_osu_files(zip_path, creator_id):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall('temp_osz')  # Extract to temporary directory

    # Iterate over the extracted files
    for file_name in os.listdir('temp_osz'):
        if file_name.endswith('.osu'):
            osu_file_path = os.path.join('temp_osz', file_name)
            print(f"Modifying: {osu_file_path}")
            with open(osu_file_path, 'r+', encoding='utf-8') as osu_file:
                content = osu_file.readlines()

                # Modify Creator: field and handle difficulty names
                for i, line in enumerate(content):
                    if line.startswith('Creator:'):
                        content[i] = f"Creator: {creator_id}\n"  # Update to the mapper's user ID
                    elif line.startswith('BeatmapID:'):
                        content[i] = "BeatmapID: 0\n"  # Set to 0
                    elif line.startswith('BeatmapSetID:'):
                        content[i] = "BeatmapSetID: -1\n"  # Set to -1
                    elif line.startswith('Version:'):
                        version_line = line.strip()
                        start_index = version_line.index(':') + 1  # Start after 'Version:'
                        version_name = version_line[start_index:].strip()

                        if "'" in version_name:
                            apostrophe_index = version_name.index("'")
                            if apostrophe_index + 1 < len(version_name) and version_name[apostrophe_index + 1] == 's':
                                # Remove everything up to and including the 's
                                content[i] = f"Version: {version_name[apostrophe_index + 2:].strip()}\n"
                            else:
                                # Remove everything up to and including the apostrophe
                                content[i] = f"Version: {version_name[apostrophe_index + 1:].strip()}\n"
                        else:
                            # If no apostrophe, leave unchanged
                            content[i] = line  # Keep the original line

                # Seek to the start of the file and write changes
                osu_file.seek(0)
                osu_file.writelines(content)
                osu_file.truncate()  # Remove any leftover data

            # Rename the .osu file
            new_file_name = f"{file_name.split('.osu')[0]} ({creator_id}).osu"
            new_file_path = os.path.join('temp_osz', new_file_name)
            os.rename(osu_file_path, new_file_path)

    # Create a new .osz file with the modified .osu files
    if not os.path.exists('Maps'):
        os.makedirs('Maps')  # Create Maps directory if it doesn't exist

    new_osz_file_name = os.path.join('Maps', f"{zip_path.replace('.osz', '_modified.osz')}")
    with zipfile.ZipFile(new_osz_file_name, 'w') as new_zip:
        for file_name in os.listdir('temp_osz'):
            new_zip.write(os.path.join('temp_osz', file_name), arcname=file_name)

    shutil.rmtree('temp_osz')  # Clean up temporary directory
    print(f"Created modified .osz: {new_osz_file_name}")



# Function to process the URLs from the text file
def process_osz_files(file_path):
    urls = get_urls_from_file(file_path)

    for url in urls:
        print(f"Processing URL: {url}")
        mapset_id = extract_mapset_id(url)  # Extract mapset ID from the URL

        if not mapset_id:
            print(f"Error: Could not extract mapset ID from URL: {url}")
            continue

        # Fetch mapset metadata using the mapset ID
        try:
            mapset_metadata = get_mapset_metadata(mapset_id)
        except requests.exceptions.HTTPError as e:
            print(f"Failed to fetch metadata for {mapset_id}: {e}")
            continue

        # Get creator information
        creator_id = mapset_metadata.get('user_id')
        if creator_id is None:
            print("Error: Creator information not found in the mapset metadata.")
            continue
        
        print(f"Mapper User ID: {creator_id}")

        # Construct download URL for the .osz file
        download_url = f"https://catboy.best/d/{mapset_id}"
        response = requests.get(download_url, allow_redirects=True)  # Allow redirects if necessary
        
        # Check if the response is okay
        if response.status_code != 200:
            print(f"Error downloading {download_url}: {response.status_code} - {response.text}")
            continue

        # Save the .osz file locally
        osz_file_name = f"{mapset_id}.osz"
        with open(osz_file_name, 'wb') as file:
            file.write(response.content)

        print(f"Downloaded: {osz_file_name} - Size: {len(response.content)} bytes")

        # Modify the .osu files inside the .osz
        modify_osu_files(osz_file_name, creator_id)

        # Delete the original .osz file after modification
        os.remove(osz_file_name)
        print(f"Deleted original .osz: {osz_file_name}")

# Example file path for the URLs
file_path = 'urls.txt'

# Run the processing function
if __name__ == "__main__":
    try:
        process_osz_files(file_path)
    except Exception as e:
        print(f"Error: {e}")
