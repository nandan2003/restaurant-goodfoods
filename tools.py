import data_manager
from datetime import datetime
import json

# --- Tool Functions ---

def get_available_restaurants(date: str, time_slot: str, party_size: int) -> str:
    """
    Gets all available restaurants for a given date, time slot, and party size.
    Returns a JSON string of a list of restaurants.
    """
    print(f"Searching availability: Date: {date}, Slot: {time_slot}, Size: {party_size}")
    
    try:
        availability_df = data_manager.get_availability(date)
        if availability_df.empty:
            return f"No availability data found for {date}."
        
        if time_slot not in availability_df.columns:
            return f"Error: '{time_slot}' is not a valid time slot."
        
        # Calculate required tables
        tables_needed = data_manager.calculate_tables_needed(party_size)
        
        # Filter restaurants that have enough tables
        available = availability_df[availability_df[time_slot] >= tables_needed]
        
        if available.empty:
            return f"No restaurants have {tables_needed} table(s) available for {party_size} guests at {time_slot} on {date}."
        
        # Select columns to return to the user
        cols_to_show = ['Name', 'Location', 'Address', 'Phone', time_slot]
        available_restaurants = available[cols_to_show].copy()
        
        # Rename the time_slot column for clarity
        available_restaurants.rename(columns={time_slot: 'Tables_Available'}, inplace=True)
        
        # Convert to JSON string
        return available_restaurants.to_json(orient='records')
        
    except Exception as e:
        print(f"ERROR in get_available_restaurants: {e}")
        return f"An unexpected error occurred: {e}"


def book_table(customer_name: str, customer_email: str, customer_phone: str, 
               restaurant_name: str, party_size: int, date: str, time_slot: str, 
               special_requests: str = "") -> str:
    """
    Books a table for a given restaurant, date, time, and party size.
    This involves checking availability, creating a booking record, 
    and updating the availability tracker.
    """
    print(f"Attempting to book table: {restaurant_name}, Date: {date}, Slot: {time_slot}, Size: {party_size}")
    
    try:
        # --- Step 1: Check restaurant and get address ---
        restaurants_df = data_manager.get_restaurant_data()
        restaurant_row = restaurants_df[restaurants_df['name'] == restaurant_name]
        
        if restaurant_row.empty:
            return f"Error: Restaurant '{restaurant_name}' not found."
        
        address = restaurant_row.iloc[0]['address']

        # --- Step 2: Check Availability *BEFORE* booking ---
        tables_needed = data_manager.calculate_tables_needed(party_size)
        
        availability_df = data_manager.get_availability(date)
        if availability_df.empty:
            return f"Error: Could not load availability data for {date}."
        
        resto_avail = availability_df[availability_df['Name'] == restaurant_name]
        
        if resto_avail.empty:
            return f"Error: Restaurant '{restaurant_name}' not found in availability tracker for {date}."

        if time_slot not in resto_avail.columns:
            return f"Error: Time slot '{time_slot}' is invalid."
            
        current_tables = resto_avail.iloc[0][time_slot]
        
        if current_tables < tables_needed:
            return (f"Booking failed: Not enough tables available at '{restaurant_name}' "
                    f"for {party_size} guests at {time_slot}. "
                    f"Only {current_tables} table(s) left.")

        # --- Step 3: Availability is confirmed, proceed with booking ---
        booking_details = {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "restaurant_name": restaurant_name,
            "restaurant_address": address,
            "party_size": party_size,
            "time_slot": time_slot,
            "special_requests": special_requests
        }
        
        # This function adds the booking and returns the full record
        new_booking = data_manager.add_booking(date, booking_details)
        
        # --- Step 4: Update the Availability Tracker (The Fix) ---
        
        # We *subtract* tables, so the change is negative
        tables_change = -tables_needed # Using tables_needed from our pre-check
        
        success = data_manager.update_availability(
            date_str=date,
            restaurant_name=restaurant_name,
            time_slot=time_slot,
            tables_change=tables_change
        )
        
        if not success:
            # Critical Error: Booking was made, but tracker update failed!
            # This is called a "rollback"
            data_manager.update_booking_status(date, new_booking['booking_id'], 'CANCELLED (Tracker Error)')
            print(f"CRITICAL: Booking {new_booking['booking_id']} created but tracker update failed. Rolling back.")
            return "Error: Booking created but failed to update availability. Booking has been automatically cancelled. Please try again."

        # --- Step 5: Success ---
        # Return a clean JSON string for the agent
        return json.dumps({
            "status": "confirmed",
            "booking_id": new_booking['booking_id'],
            "restaurant_name": restaurant_name,
            "party_size": party_size,
            "date": date,
            "time_slot": time_slot,
            "tables_reserved": tables_needed
        })

    except Exception as e:
        print(f"ERROR in book_table: {e}")
        return f"An unexpected error occurred: {e}"


def get_booking_details(booking_id: str, date: str) -> str:
    """
    Retrieves the details for a specific booking ID and date.
    Returns a JSON string of the booking details.
    """
    print(f"Getting details for booking: {booking_id} on {date}")
    
    try:
        bookings_df = data_manager.get_bookings(date)
        booking_row = bookings_df[bookings_df['booking_id'] == booking_id]
        
        if booking_row.empty:
            return f"Error: Booking ID '{booking_id}' not found for date {date}."
        
        # Convert the single row to a JSON object string
        return booking_row.iloc[0].to_json()
        
    except Exception as e:
        print(f"ERROR in get_booking_details: {e}")
        return f"An unexpected error occurred: {e}"


def cancel_booking(booking_id: str, date: str) -> str:
    """
    Cancels a booking by its ID and the date.
    This updates the booking status and returns the tables
    to the availability tracker.
    """
    print(f"Attempting to cancel booking: {booking_id} for date: {date}")
    
    try:
        # --- Step 1: Find the booking ---
        bookings_df = data_manager.get_bookings(date)
        booking_row = bookings_df[bookings_df['booking_id'] == booking_id]
        
        if booking_row.empty:
            return f"Error: Booking ID '{booking_id}' not found for date {date}."
            
        booking = booking_row.iloc[0]
        
        # --- Step 2: Check if already cancelled ---
        if booking['status'].lower() in ['cancelled', 'cancelled (tracker error)']:
            return f"Booking {booking_id} is already cancelled."
            
        # --- Step 3: Update Availability (ADD tables back) ---
        tables_to_return = booking['tables_reserved']
        restaurant_name = booking['restaurant_name']
        time_slot = booking['time_slot']
        
        # We *add* tables back, so the change is positive
        tables_change = tables_to_return
        
        success = data_manager.update_availability(
            date_str=date,
            restaurant_name=restaurant_name,
            time_slot=time_slot,
            tables_change=tables_change
        )
        
        if not success:
            # If this fails, we should NOT cancel the booking, as it would
            # create an inconsistency (cancelled booking but tables not returned).
            print(f"ERROR: Failed to update availability for cancellation of {booking_id}.")
            return "Error: Could not return tables to tracker. Cancellation failed. Please contact support."

        # --- Step 4: Update booking status ---
        status_updated = data_manager.update_booking_status(date, booking_id, "cancelled")
        
        if not status_updated:
            # This is another critical error. We returned tables but failed to
            # update the booking status. We must try to "roll back" the availability.
            print(f"CRITICAL: Tracker updated but booking status update failed for {booking_id}. Attempting to roll back tracker.")
            data_manager.update_availability(date, restaurant_name, time_slot, -tables_to_return) # Subtract tables again
            return "Error: A critical error occurred. Availability was updated but booking status failed. All changes have been rolled back. Please try again."

        # --- Step 5: Success ---
        return json.dumps({
            "status": "cancelled",
            "booking_id": booking_id,
            "restaurant_name": restaurant_name,
            "tables_returned": int(tables_to_return) # Ensure it's an int
        })
        
    except Exception as e:
        print(f"ERROR in cancel_booking: {e}")
        return f"An unexpected error occurred: {e}"


# --- Tool Definitions (for the LLM) ---
# (This section is unchanged from your original file)

tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "get_available_restaurants",
            "description": "Get a list of available restaurants based on date, time, and party size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for the reservation, e.g., '30.10.2025'."
                    },
                    "time_slot": {
                        "type": "string",
                        "description": "The desired time slot, e.g., '07:00 PM'."
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "The number of guests in the party."
                    }
                },
                "required": ["date", "time_slot", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_table",
            "description": "Book a table at a specific restaurant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Full name of the customer."},
                    "customer_email": {"type": "string", "description": "Email address of the customer."},
                    "customer_phone": {"type": "string", "description": "Phone number of the customer."},
                    "restaurant_name": {"type": "string", "description": "The name of the restaurant."},
                    "party_size": {"type": "integer", "description": "The number of guests."},
                    "date": {"type": "string", "description": "The date for the reservation, e.g., '30.10.2025'."},
                    "time_slot": {"type": "string", "description": "The desired time slot, e.g., '07:00 PM'."},
                    "special_requests": {"type": "string", "description": "Any special requests for the booking."}
                },
                "required": ["customer_name", "customer_email", "customer_phone", "restaurant_name", "party_size", "date", "time_slot"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_details",
            "description": "Retrieve the details of an existing booking using a booking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "The unique ID of the booking."},
                    "date": {"type": "string", "description": "The date of the booking, e.g., '30.10.2025'."}
                },
                "required": ["booking_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an existing booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "string", "description": "The unique ID of the booking to cancel."},
                    "date": {"type": "string", "description": "The date of the booking, e.g., '30.10.2025'."}
                },
                "required": ["booking_id", "date"]
            }
        }
    }
]

# --- Tool Dispatcher ---
# (This section is unchanged from your original file)

tool_functions = {
    "get_available_restaurants": get_available_restaurants,
    "book_table": book_table,
    "get_booking_details": get_booking_details,
    "cancel_booking": cancel_booking
}
