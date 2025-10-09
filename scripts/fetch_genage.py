# filename: get_genage_data.py
# Description: Downloads the GenAge zip archive, extracts the human genes CSV,
#              and saves it to the data/raw directory.

import pandas as pd
import requests
import zipfile
import io

def download_and_extract_genage_zip(zip_url: str):
    """
    Downloads a zip archive from a URL, finds the 'genage_human.csv' file within it,
    and loads it into a pandas DataFrame.

    Args:
        zip_url (str): The URL of the .zip file to download.

    Returns:
        pandas.DataFrame: A DataFrame containing the GenAge data, or None if it fails.
    """
    print(f"Attempting to download and extract data from: {zip_url}")
    
    try:
        # Step 1: Download the zip file's content using requests
        response = requests.get(zip_url)
        response.raise_for_status() # Raise an exception for bad status codes

        # Step 2: Open the zip file in memory from the downloaded content
        zip_archive = zipfile.ZipFile(io.BytesIO(response.content))
        
        # The filename we want to extract from the zip archive
        target_csv = 'genage_human.csv'

        # Step 3: Read the specific CSV file from the zip archive into a DataFrame
        with zip_archive.open(target_csv) as csv_file:
            genage_df = pd.read_csv(csv_file)
            print(f"✅ Successfully extracted and loaded '{target_csv}'!")
            return genage_df

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download the file: {e}")
        return None
    except KeyError:
        print(f"❌ Could not find the file '{target_csv}' inside the zip archive.")
        print(f"   Available files: {zip_archive.namelist()}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == "__main__":
    # --- How to use the script ---
    
    # The new URL you provided for the zip archive
    url = "https://genomics.senescence.info/genes/human_genes.zip"
    
    # Get the data
    genage_data = download_and_extract_genage_zip(url)

    if genage_data is not None:
        # Display the first 5 rows to verify
        print("\n--- GenAge Data (First 5 Rows) ---")
        print(genage_data.head())

        # Save the data to a CSV file for your other scripts and notebooks
        # Make sure the 'data/raw' directory exists first!
        output_filename = "data/raw/genage_human.csv"
        genage_data.to_csv(output_filename, index=False)
        print(f"\nData saved to {output_filename}")