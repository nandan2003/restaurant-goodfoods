import pandas as pd
from pathlib import Path
import math
import uuid
from datetime import datetime

# --- Configuration ---
RESTAURANT_DATA_FILE = 'restaurantData.csv'
BASE_TABLE_CAPACITY = 10  # Default tables per slot for a new restaurant
AVG_GUESTS_PER_TABLE = 4  # Assumption for calculating required tables

# Time slots as they appear in the tracker file
TIME_SLOTS = [
    "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM", 
    "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM", 
    "08:00 PM", "09:00 PM", "10:00 PM"
]

# --- File Path Helpers ---

def get_tracker_filepath(date_str: str) -> Path:
    """Gets the file path for the tracker CSV for a given date."""
    return Path(f"restaurant_booking_tracker[{date_str}].csv")

def get_bookings_filepath(date_str: str) -> Path:
    """Gets the file path for the bookings CSV for a given date."""
    return Path(f"bookings[{date_str}].csv")

# --- Creation Functions ---

def create_new_tracker_file(date_str: str):
    """
    Creates a new restaurant_booking_tracker file for a given date,
    populating it from restaurantData.csv.
    """
    print(f"Creating new tracker file for {date_str}...")
    try:
        df_restaurants = pd.read_csv(RESTAURANT_DATA_FILE)
        
        # Select base columns
        tracker_df = df_restaurants[['name', 'location', 'address', 'phone']].copy()
        
        # Add time slot columns with default capacity
        for slot in TIME_SLOTS:
            tracker_df[slot] = BASE_TABLE_CAPACITY
            
        # Rename columns to match tracker format
        tracker_df = tracker_df.rename(columns={
            'name': 'Name',
            'location': 'Location',
            'address': 'Address',
            'phone': 'Phone'
        })

        tracker_df.to_csv(get_tracker_filepath(date_str), index=False)
        print(f"Successfully created {get_tracker_filepath(date_str)}")
        
    except FileNotFoundError:
        print(f"ERROR: Cannot create tracker. {RESTAURANT_DATA_FILE} not found.")
    except Exception as e:
        print(f"ERROR creating tracker file: {e}")

def create_new_bookings_file(date_str: str):
    """Creates a new, empty bookings file for a given date with correct headers."""
    print(f"Creating new bookings file for {date_str}...")
    headers = [
        "booking_id", "customer_name", "customer_email", "customer_phone",
        "restaurant_name", "restaurant_address", "party_size", "time_slot",
        "tables_reserved", "status", "special_requests", "created_at", "updated_at"
    ]
    df = pd.DataFrame(columns=headers)
    df.to_csv(get_bookings_filepath(date_str), index=False)

# --- Data Reading Functions ---

def get_restaurant_data():
    """Loads the main restaurant data file."""
    try:
        return pd.read_csv(RESTAURANT_DATA_FILE)
    except FileNotFoundError:
        print(f"ERROR: {RESTAURANT_DATA_FILE} not found.")
        return pd.DataFrame() # Return empty df

def get_availability(date_str: str) -> pd.DataFrame:
    """
    Loads the availability tracker for a given date.
    Creates it if it doesn't exist.
    """
    filepath = get_tracker_filepath(date_str)
    if not filepath.exists():
        create_new_tracker_file(date_str)
        
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError: # In case creation failed
        return pd.DataFrame()

def get_bookings(date_str: str) -> pd.DataFrame:
    """
    Loads the bookings for a given date.
    Creates it if it doesn't exist.
    """
    filepath = get_bookings_filepath(date_str)
    if not filepath.exists():
        create_new_bookings_file(date_str)
        
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError: # In case creation failed
        return pd.DataFrame()

# --- Data Writing Functions ---

def calculate_tables_needed(party_size: int) -> int:
    """Calculates tables needed based on party size."""
    return math.ceil(party_size / AVG_GUESTS_PER_TABLE)

def add_booking(date_str: str, booking_details: dict) -> dict:
    """
    Adds a new booking to the bookings[date].csv file.
    Returns the full booking record with booking_id.
    """
    filepath = get_bookings_filepath(date_str)
    df = get_bookings(date_str) # Ensures file exists
    
    now = datetime.now().isoformat()
    
    new_booking = {
        "booking_id": str(uuid.uuid4())[:8], # Short unique ID
        "customer_name": booking_details.get("customer_name"),
        "customer_email": booking_details.get("customer_email"),
        "customer_phone": booking_details.get("customer_phone"),
        "restaurant_name": booking_details.get("restaurant_name"),
        "restaurant_address": booking_details.get("restaurant_address", ""), # Get from details
        "party_size": booking_details.get("party_size"),
        "time_slot": booking_details.get("time_slot"),
        "tables_reserved": calculate_tables_needed(booking_details.get("party_size", 0)),
        "status": "confirmed",
        "special_requests": booking_details.get("special_requests", ""),
        "created_at": now,
        "updated_at": now
    }
    
    df = pd.concat([df, pd.DataFrame([new_booking])], ignore_index=True)
    df.to_csv(filepath, index=False)
    
    return new_booking

def update_booking_status(date_str: str, booking_id: str, new_status: str) -> bool:
    """Updates the status of an existing booking."""
    filepath = get_bookings_filepath(date_str)
    df = get_bookings(date_str)
    
    if booking_id not in df['booking_id'].values:
        return False # Booking not found
        
    booking_index = df[df['booking_id'] == booking_id].index
    
    df.loc[booking_index, 'status'] = new_status
    df.loc[booking_index, 'updated_at'] = datetime.now().isoformat()
    
    df.to_csv(filepath, index=False)
    return True

def update_availability(date_str: str, restaurant_name: str, time_slot: str, tables_change: int) -> bool:
    """
    Updates the table availability in the tracker.
    `tables_change` can be positive (adding tables back) or negative (booking).
    """
    filepath = get_tracker_filepath(date_str)
    df = get_availability(date_str) # Ensures file exists
    
    # Find the row for the restaurant
    # Note: Assumes restaurant_name is a unique identifier. 
    # A real-world app might use a unique restaurant_id.
    row_index = df[df['Name'] == restaurant_name].index
    
    if row_index.empty:
        print(f"ERROR: Restaurant '{restaurant_name}' not found in tracker.")
        return False
        
    if time_slot not in df.columns:
        print(f"ERROR: Time slot '{time_slot}' not a valid column.")
        return False
        
    # Update the value
    current_tables = df.loc[row_index, time_slot].iloc[0]
    new_table_count = current_tables + tables_change
    
    if new_table_count < 0:
        print(f"ERROR: Cannot book. Not enough tables. Trying to set to {new_table_count}")
        return False # Should be checked before calling, but as a safeguard
        
    df.loc[row_index, time_slot] = new_table_count
    df.to_csv(filepath, index=False)
    
    return True