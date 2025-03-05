#!/usr/bin/env python3
import os

# Base URL for the WebDAV directory
base_url = "https://dadosabertos.dgterritorio.gov.pt/webdav/ortos/ortosat2023/1_OrtoSat2023_CorVerdadeira/1_Seccoes_OrtoSat2023_CorVerdadeira"

# Get the number of URLs to print from the environment variable NUM_URLS (default: 20)
num_urls = int(os.getenv("NUM_URLS", 20))

count = 0
# Loop through folders from 0000 to 4800 in steps of 100
for folder in range(0, 4801, 100):
    folder_suffix = f"{folder:04d}"
    folder_url = f"{base_url}/Seccoes_{folder_suffix}"
    # For each folder, generate file numbers from folder value to folder value + 99
    for sub in range(0, 100):
        file_num = folder + sub
        file_name = f"OrtoSat2023_{file_num:04d}_CorVerdadeira.tif"
        full_url = f"{folder_url}/{file_name}"
        print(full_url)
        count += 1
        if count >= num_urls:
            exit(0)
