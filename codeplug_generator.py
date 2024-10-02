#!/usr/bin/env python3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2024 Luca Martini
import argparse
import requests
import pandas as pd
import csv
import json  # Add this line to import the JSON module
import sys
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from collections import defaultdict
# Keep track of used channel names to ensure uniqueness
# Declare the global variable to store channel names per state
channels_by_state = defaultdict(list)
channels_by_network = defaultdict(list)
# map_data = None

# Initialize the used_channel_names set globally
used_channel_names = set()

def download_radioid_map(url="https://radioid.net/static/map.json", local_filename='map.json'):
    """
    Downloads JSON data from the given URL and saves it to a local file named map.json.
    Loads and returns the JSON data after saving it. If the local file exists and is less
    than 24 hours old, it loads the data from the local file instead of downloading it.

    Args:
        url (str): The URL to download the JSON data from. Default is the RadioID map URL.
        local_filename (str): The name of the local file to save the JSON data. Default is 'map.json'.
    
    Returns:
        dict or list: Parsed JSON data loaded from the downloaded file or from the local file.
    """
    # Check if the local file exists
    if os.path.exists(local_filename):
        # Check the modification time of the file
        file_mod_time = os.path.getmtime(local_filename)
        current_time = time.time()
        
        # If the file is less than 24 hours old, load the JSON from the local file
        if (current_time - file_mod_time) < 24 * 3600:  # 24 hours in seconds
            print(f"Loading data from local file {local_filename} (less than 24h old)")
            try:
                with open(local_filename, 'r') as json_file:
                    data = json.load(json_file)
                return data
            except Exception as e:
                print(f"Error loading JSON from {local_filename}: {e}")
                return None

    # If the file is older than 24 hours or does not exist, download the data
    print(f"Downloading data from {url} and saving to {local_filename}")
    try:
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            with open(local_filename, 'w') as json_file:
                json.dump(response.json(), json_file, indent=4)
            print(f"JSON data downloaded and saved to {local_filename}")
            
            # Load the JSON content from the file
            with open(local_filename, 'r') as json_file:
                data = json.load(json_file)
            return data
        else:
            print(f"Error: Unable to download data. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def lookup_record_by_id(record_id, map_data):
    """
    Look up a record in the JSON data by a specific id and return the longitude and latitude.
    
    Args:
        record_id (int or str): The id to search for.
        json_data (dict or list): The loaded JSON data to search within.

    Returns:
        tuple: (longitude, latitude) if the record is found, or (None, None) if not found.
    """
    # Iterate over all records in the JSON data
    for marker in map_data.get('markers', []):  # Assuming 'markers' contains the list of records
        if str(marker.get('locator', '')) == str(record_id):  # Compare as string to handle int/str cases
            lon = marker.get('lng', None)
            lat = marker.get('lat', None)
            return lon, lat  # Return the longitude and latitude if found
    return 0, 0  # Return (0, 0) if no matching record is found

def write_zone_to_csv(output_file, max_channels=180):
    """
    Write the global channels_by_state dictionary to a CSV file where the zone name is the state,
    and up to 180 channels are listed in separate columns. If a state has fewer than 180 channels, 
    the remaining cells will be left empty.

    Args:
        output_file (str): The path to the output CSV file.
        max_channels (int): The maximum number of channels per state (default is 180).
    """
    # Use the global channels_by_state dictionary
    global channels_by_state
    # additional networks get put in their own zone
    global channels_by_network
    # Create the header for the CSV (Zone Name, Channel1, Channel2, ..., Channel180)
    header = ['Zone Name'] + [f'Channel{i}' for i in range(1, max_channels + 1)]
    # Open the CSV file for writing
    with open(output_file, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write the header
        writer.writerow(header)

        # Write each state (zone) and its associated channels
        for state, channels in channels_by_state.items():
            # Limit channels to max_channels and pad with empty strings if there are fewer
            row = [state] + channels[:max_channels] + [''] * (max_channels - len(channels))
            writer.writerow(row)
        # Write each network (zone) and its associated channels
        for network, channels in channels_by_network.items():
            # Limit channels to max_channels and pad with empty strings if there are fewer
            row = [network] + channels[:max_channels] + [''] * (max_channels - len(channels))
            writer.writerow(row)

    print(f"Zones by state have been written to {output_file}")
    
def fetch_lat_long_with_selenium(repeater_id):
    # Set up Chrome options with performance optimizations
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Enable headless mode
    chrome_options.add_argument('--no-sandbox')  # Useful in some Linux environments
    chrome_options.add_argument('--disable-dev-shm-usage')  # For limited resource problems
    chrome_options.add_argument('--disable-gpu')  # Headless mode doesn't need GPU

    # Path to ChromeDriver on your system
    service = Service('/usr/lib64/chromium-browser/chromedriver')

    # Initialize the Chrome WebDriver with the Service object and options
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Construct the URL for the given Radio ID
        url = f"https://brandmeister.network/?page=device-edit&id={repeater_id}"
        
        # Open the page
        driver.get(url)
        
        # Find the latitude and longitude elements by their ID or name
        lat_element = driver.find_element(By.NAME, 'lat')
        lng_element = driver.find_element(By.NAME, 'lng')

        # Get the values of latitude and longitude
        latitude = lat_element.get_attribute('value')
        longitude = lng_element.get_attribute('value')
        # Validate that both latitude and longitude are numbers
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            # If either value is not a number, return 0, 0
            return 0, 0

        return latitude, longitude

    except Exception as e:
        print(f"Error occurred: {e}")
        return None, None

    finally:
        # Close the browser
        driver.quit()

# Function to calculate Tx Frequency based on Rx Frequency and Offset
def calculate_tx_frequency(rx_frequency, offset):
    try:
        return float(rx_frequency) + float(offset)
    except ValueError:
        # Return an empty string if there's an issue with the conversion
        return ''

def get_unique_channel_name(base_name):
    """
    Generate a unique channel name that is no longer than 16 characters.
    If the base name already exists, append a numeric suffix to ensure uniqueness.
    """
    # Truncate the base name to 16 characters
    base_name = base_name[:16]
    
    # If the name is already unique, return it
    if base_name not in used_channel_names:
        used_channel_names.add(base_name)
        return base_name
    
    # If the base name exists, append a number to ensure uniqueness
    suffix = 1
    unique_name = base_name[:15]  # Reserve space for the suffix
    while unique_name in used_channel_names:
        suffix_str = hex(suffix)[2:].upper()  # Remove '0x' prefix and convert to uppercase
        # Create a new unique name by appending the suffix
        unique_name = base_name[:15 - len(suffix_str)] + suffix_str
        suffix += 1
    
    # Add the new unique name to the set
    used_channel_names.add(unique_name)
    return unique_name

def map_repeater_to_csv(repeater, map_data=None, no_location_lookup=False, additional_networks=None):
    """
    Map repeater data to CSV format and optionally perform location lookup.

    Args:
        repeater (dict): The dictionary containing repeater details.
        no_location_lookup (bool): If True, location lookup is disabled (latitude and longitude will be set to 0).
        additional_networks (list): A list of additional networks to match.
    """
    use_location = 'No'
    if additional_networks is None:
        additional_networks = []

    # Ensure that the repeater is a dictionary
    if not isinstance(repeater, dict):
        print(f"Skipping unexpected data format: {repeater}")
        return None

    base_channel_name = f"{repeater.get('City', '')} {repeater.get('Callsign', '')}".strip()
    channel_name = get_unique_channel_name(base_channel_name)
    rx_frequency = repeater.get('Frequency', '')
    offset = repeater.get('Offset', 0)
    tx_frequency = calculate_tx_frequency(rx_frequency, offset)
    radioid= repeater.get('id', 0)
    network = repeater.get('IPSCNetwork', '')
    if network is None:
        network = ''
    else:
        network = network.lower()
    # Skip if network does not contain 'bm', 'brand', 'tgif', 'adn', or 'dmr', 
    # and if it's not in additional networks
    if (
        'bm' not in network and 'bran' not in network and 'tgif' not in network and 'adn' not in network and 'dmr-plus' not in network 
        and network not in [n.lower() for n in additional_networks]
    ):
        print(f"Skipping repeater due to non-matching network: {network}")
        return None
    
    # Get the state for the repeater
    state = repeater.get('State', 'Unknown')
    # Add the channel name to the list of the corresponding state
    channels_by_state[state].append(channel_name)
    # if we have additional networks add the channels here
    if network in [n.lower() for n in additional_networks]:
           channels_by_network[network].append(channel_name)
    
    # Perform location lookup only if no_location_lookup is False
    if no_location_lookup:
        lat = 0
        lon = 0
    elif "bm" in network or 'bran' in network:    # only fetch repeater location if it is a Bm repeater
        lat, lon = fetch_lat_long_with_selenium(radioid)
        # If fetch_lat_long_with_selenium returns (0, 0), fall back to lookup_record_by_id
        if lat == 0 and lon == 0:
            print(f"Warning: fetch_lat_long_with_selenium returned (0, 0) for radioid {radioid}. Channel Name {channel_name} Falling back to lookup_record_by_id.")
            lon, lat = lookup_record_by_id(radioid, map_data)
    else:
        # use radioid only
        lon, lat = lookup_record_by_id(radioid, map_data)
        
# set user location flag
    if lat != 0 and lon != 0:
          user_lopcation= 'yes'
    if "bm" in network or 'brand' in network:
        tg_list = 'BM'
    else:
        tg_list = network.upper()
        
    return {
        'Channel Number': repeater.get('channel_number',''),  # incremented
        'Channel Name': channel_name,
        'Channel Type': 'Digital',  # Placeholder for now
        'Rx Frequency': rx_frequency,
        'Tx Frequency': tx_frequency,
        'Bandwidth (kHz)': '',  # Not available in the API
        'Colour Code': repeater.get('ColorCode', ''),
        'Timeslot': '1', # always 1 for opendm77 as it is settable by keyboard
        'Contact': 'None',  # Trustee as contact
        'TG List': tg_list,  # Placeholder
        'DMR ID': 'None',
        'TS1_TA_Tx': 'APRS+Text',  # Placeholder
        'TS2_TA_Tx ID': 'APRS+Text',  # Placeholder
        'RX Tone': '',  # Placeholder
        'TX Tone': '',  # Placeholder
        'Squelch': '',  # Placeholder
        'Power': 'Master',  # Placeholder
        'Rx Only': 'No',  # Placeholder
        'Zone Skip': 'No',  # Placeholder
        'All Skip': 'No',  # Placeholder
        'TOT': '0',  # Placeholder
        'VOX': 'Off',  # Placeholder
        'No Beep': 'No',  # Placeholder
        'No Eco': 'No',  # Placeholder
        'APRS': 'None',  # Placeholder
        'Latitude': lat,  
        'Longitude': lon,
        'Roaming': 'No',  # Placeholder
        'Use location': use_location
    }


# Function to map API data to CSV format

# Function to fetch repeater data for given states

def fetch_repeaters(states=None, cities=None, countries=None):
    """
    Fetch repeaters based on the provided states, cities, and countries.
    
    Args:
        states (list): List of states to filter repeaters.
        cities (list): List of cities to filter repeaters.
        countries (list): List of countries to filter repeaters.
        
    Returns:
        list: List of repeater objects.
    """
    base_url = 'https://radioid.net/api/dmr/repeater/'
    # Build query parameters for the API call
    params = []
    
    # Add states, cities, and countries to the params as query parameters
    if states:
        params.extend([('state', state) for state in states])
    if cities:
        params.extend([('city', city) for city in cities])
    if countries:
        params.extend([('country', country) for country in countries])
    # Make the API request with the built parameters
    response = requests.get(base_url, params=params)

    # Check if the response was successful
    if response.status_code == 200:
        try:
            # Try parsing the JSON response
            return response.json()
        except ValueError:
            print("Error: Unable to parse JSON response")
            return []
    elif response.status_code == 406:
        # Handle 406 Not Acceptable specifically with a custom message
        print("No repeaters match search")
        sys.exit(0)  # Exit the program cleanly with status 0
    else:
        print(f"Error: Unable to fetch data. Status code: {response.status_code}")
        sys.exit(1)  # Exit with a failure code if any other error occurs
        
# Define a function to format the repeater data
def format_repeater_data(data,chn):
    """
    Format repeater data from the API response, including the 'id' field.

    Args:
        api_response (str): JSON string of the API response.

    Returns:
        dict: A dictionary with the total count of repeaters and a list of formatted repeaters.
    """
    # Extract count and results
    total_count = data.get("count", 0)
    repeaters = data.get("results", [])
    
    # Format the repeater information
    formatted_repeaters = []
    #initialize channel correctly
    chn -= 1
    for repeater in repeaters:
        # Extract and format the details, converting HTML line breaks to semicolons for clarity
        details = repeater.get("details", "")  # Get the 'details' field, default to an empty string
        details_clean = details.replace("<br>", "; ") if details else ""  # Only replace if details is not None or empty
        chn += 1
        formatted_repeaters.append({
            "channel_number": chn,
            "id": repeater.get("id", "N/A"),
            "Callsign": repeater.get("callsign", "N/A"),
            "City": repeater.get("city", "N/A"),
            "State": repeater.get("state", "N/A"),
            "Country": repeater.get("country", "N/A"),
            "Frequency": repeater.get("frequency", "N/A"),
            "Offset": repeater.get("offset", "N/A"),
            "IPSCNetwork": repeater.get("ipsc_network", "N/A"),
            "Trustee": repeater.get("trustee", "N/A"),
            "Details": repeater.get("details", "N/A"),
            "ColorCode": repeater.get("color_code", "N/A"),
            "TimeSlotLinked": repeater.get("ts_linked", "N/A")
        })
    
    # Return the formatted data
    return formatted_repeaters

# Main function to handle command-line arguments and run the program
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Fetch DMR repeaters for specified states and save them to CSV.")
    parser.add_argument('--channels', type=str, default='Channels.csv', help='Channels CSV file name')
    parser.add_argument('--zones', type=str, default='Zones.csv', help='Zones CSV file name')
    parser.add_argument('--channel_number', type=int, default=1, help="Starting channel number")
    parser.add_argument('--no-location-lookup', action='store_true', help="Disable location lookup")

    # Use nargs='?' to capture the entire argument string (with commas)
    parser.add_argument('--cities', type=str, nargs='?', help="Comma-separated list of cities (e.g., New York,Los Angeles,Denver)")
    parser.add_argument('--countries', type=str, nargs='?', help="Comma-separated list of countries (e.g., United States,Canada,Mexico)")
    parser.add_argument('--states', type=str, nargs='?', help='Comma-separated list of states (e.g., Vermont,New York)')
   # Add --additional-networks option
    parser.add_argument('--additional-networks', type=str, help="Comma-separated list of additional network names")

 #   parser.add_argument('states', metavar='state', type=str, nargs='+',
 #                       help='List of states to fetch repeaters for (e.g., vermont new york)')
# Parse the arguments
    args = parser.parse_args()
    
# Process the comma-separated lists
    cities = [city.strip() for city in args.cities.split(',')] if args.cities else []
    states = [state.strip() for state in args.states.split(',')] if args.states else []
    countries = [country.strip() for country in args.countries.split(',')] if args.countries else []
    additional_networks = [network.strip() for network in args.additional_networks.split(',')] if args.additional_networks else []

    channel_file = args.channels
    zone_file = args.zones
    seed_channel_number = args.channel_number
# Ensure at least one of states, cities, or countries is provided
    if not (states or cities or countries):
        print("Error: At least one of --states, --cities, or --countries must be provided.")
        return
# Call the function to download radioid map data
    map_data = download_radioid_map()
    if map_data is None:
        print(f"Error: No valid JSON data loaded for the map.")
# Fetch repeaters for the specified states
    repeaters = fetch_repeaters(states, cities, countries)
# format repeaters into a dict
    repeater_objects = format_repeater_data(repeaters, seed_channel_number) 
# Map the repeaters to the CSV format, filtering out None results
    mapped_data = [
        map_repeater_to_csv(repeater, map_data, no_location_lookup=args.no_location_lookup, additional_networks=additional_networks)
        for repeater in repeater_objects if repeater is not None
    ]
#    print(mapped_data)
    # Convert to a DataFrame
    df = pd.DataFrame([r for r in mapped_data if r is not None])
    print(df)    
    # Write the data to a CSV file
    df.to_csv(channel_file, index=False)
    print(f"Data has been written to {channel_file}")
    write_zone_to_csv(zone_file)
    
if __name__ == '__main__':
    main()
