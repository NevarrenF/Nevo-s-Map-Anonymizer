import requests
import shutil
import os
import zipfile

# Catboy API URL setup
base_url = "https://catboy.best"

# Function to get mapset metadata using mapset ID from Catboy API
def get_mapset_metadata(mapset_id):
    map_url = f"{base_url}/api/v2/s/{mapset_id}"
    response = requests.get(map_url)
    response.raise_for_status()  # Check for HTTP errors
    return response.json()  # Return the JSON metadata

# Function to download the beatmap file (.osz) from Catboy API
def download_beatmap(mapset_id):
    download_url = f"{base_url}/d/{mapset_id}"
    response = requests.get(download_url, stream=True)
    response.raise_for_status()  # Check for HTTP errors
    osz_file_name = f"{mapset_id}.osz"
    
    with open(osz_file_name, 'wb') as file:
        shutil.copyfileobj(response.raw, file)
    print(f"Downloaded: {osz_file_name} - Size: {os.path.getsize(osz_file_name)} bytes")
    return osz_file_name

# Function to update the Creator, BeatmapID, and BeatmapSetID fields and rename .osu files
def update_osu_creator(osz_file_name, creator_id, mapset_metadata):
    temp_dir = "temp_osz"
    os.makedirs(temp_dir, exist_ok=True)
    
    with zipfile.ZipFile(osz_file_name, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Modify each .osu file in the extracted content
    title = mapset_metadata['title']
    artist = mapset_metadata['artist']
    original_creator = mapset_metadata['creator']
    
    for filename in os.listdir(temp_dir):
        if filename.endswith(".osu"):
            osu_file_path = os.path.join(temp_dir, filename)
            with open(osu_file_path, 'r', encoding='utf-8') as file:
                content = file.readlines()

            # Update the Creator, BeatmapID, and BeatmapSetID fields
            for i, line in enumerate(content):
                if line.startswith("Creator:"):
                    content[i] = f"Creator: {creator_id}\n"
                elif line.startswith("BeatmapID:"):
                    content[i] = "BeatmapID: 0\n"
                elif line.startswith("BeatmapSetID:"):
                    content[i] = "BeatmapSetID: -1\n"

            # Write changes back to the .osu file
            with open(osu_file_path, 'w', encoding='utf-8') as file:
                file.writelines(content)
            print(f"Updated Creator, BeatmapID, and BeatmapSetID in: {filename}")

            # Rename the .osu file to include the creator's user ID
            difficulty = filename.split('[')[-1]  # Get difficulty name from the original file
            new_filename = f"{artist} - {title} ({creator_id}) [{difficulty}"
            os.rename(osu_file_path, os.path.join(temp_dir, new_filename))
            print(f"Renamed {filename} to {new_filename}")

    # Create a new .osz file with modified .osu files
    modified_osz_file = f"modified_{osz_file_name}"
    with zipfile.ZipFile(modified_osz_file, 'w') as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, temp_dir))

    # Clean up the temporary directory
    shutil.rmtree(temp_dir)
    print(f"Created modified .osz: {modified_osz_file}")

# Example list of URLs to download and process
urls = [
    "https://osu.ppy.sh/beatmapsets/2273815#osu/4844304",
]

# Main process function
def process_osz_files(urls):
    for url in urls:
        print(f"Processing URL: {url}")
        mapset_id = url.split('/')[-1]  # Extract mapset ID from the URL

        # Fetch mapset metadata
        mapset_metadata = get_mapset_metadata(mapset_id)
        creator_id = mapset_metadata.get("user_id")

        # Download the .osz file
        osz_file_name = download_beatmap(mapset_id)

        # Update .osu files inside the .osz file
        update_osu_creator(osz_file_name, creator_id, mapset_metadata)

# Run the processing function
if __name__ == "__main__":
    process_osz_files(urls)
