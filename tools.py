import json
import pandas as pd
import data_manager
from datetime import datetime
from validators import Validator # We need this to get valid slots

# --- Tool Definitions (JSON Schema) ---
# This is the "contract" for the Model (LLM)
tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "get_available_restaurants",
            "description": "Searches for restaurants based on user criteria and checks if they have any availability on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for the booking (DD.MM.YYYY)."
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "The desired cuisine (e.g., 'Italian', 'Chinese')."
                    },
                    "location": {
                        "type": "string",
                        "description": "The desired neighborhood (e.g., 'Indiranagar')."
                    },
                    "max_cost": {
                        "type": "number",
                        "description": "The maximum approximate cost for two people."
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "The minimum customer rating (out of 5)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_restaurant_details",
            "description": "Gets detailed information for a specific restaurant, including its menu items and available time slots for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date to check availability for (DD.MM.YYYY)."
                    },
                    "restaurant_name": {
                        "type": "string",
                        "description": "The exact name of the restaurant."
                    }
                },
                "required": ["date", "restaurant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_table",
            "description": "Books a table at a restaurant for a specific date, time, and party size. Requires all customer details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date for the booking (DD.MM.YYYY)."
                    },
                    "restaurant_name": {
                        "type": "string",
                        "description": "The exact name of the restaurant."
                    },
                    "time_slot": {
                        "type": "string",
                        "description": "The desired time slot (e.g., '07:00 PM'). Must be from the available slots."
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "The number of guests in the party."
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "The full name of the customer."
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "The customer's email address."
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "The customer's phone number."
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "Any special requests (e.g., 'Birthday cake')."
                    }
                },
                "required": ["date", "restaurant_name", "time_slot", "party_size", "customer_name", "customer_email", "customer_phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_bookings",
            "description": "Finds existing bookings for a given date using either a booking ID or customer details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date of the booking (DD.MM.YYYY). Agent must ask for this."
                    },
                    "booking_id": {
                        "type": "string",
                        "description": "The unique booking ID."
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "The customer's name (used if booking_id is unknown)."
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "The customer's email (used if booking_id is unknown)."
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "The customer's phone (used if booking_id is unknown)."
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancels a specific booking and adds the tables back to the tracker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "The date of the booking (DD.MM.YYYY)."
                    },
                    "booking_id": {
                        "type": "string",
                        "description": "The unique booking ID to cancel."
                    }
                },
                "required": ["date", "booking_id"]
            }
        }
    }
]

# --- Tool Function Implementations (Program Layer) ---
# All validation has been REMOVED.

def get_available_restaurants(date: str, cuisine: str = None, location: str = None, max_cost: int = None, min_rating: float = None) -> str:
    """Implementation for get_available_restaurants tool."""
    try:
        validator = Validator()
        valid_slots_to_check, error = validator.get_valid_time_slots(date)
        if error:
            return json.dumps({"status": "ok", "restaurants": [], "message": error})

        df_data = data_manager.get_restaurant_data()
        df_avail = data_manager.get_availability(date)

        if df_data.empty or df_avail.empty:
            return json.dumps({"status": "error", "message": "Could not load restaurant data."})

        # Filter static data
        if cuisine:
            df_data = df_data[df_data['cuisines'].str.contains(cuisine, case=False, na=False)]
        if location:
            df_data = df_data[df_data['location'].str.contains(location, case=False, na=False)]
        if max_cost:
            df_data['cost_cleaned'] = pd.to_numeric(df_data['approx_cost(for two people)'].str.replace(',', ''), errors='coerce')
            df_data = df_data[df_data['cost_cleaned'] <= max_cost]
        if min_rating:
            df_data['rating_cleaned'] = pd.to_numeric(df_data['rate'].str.split('/').str[0], errors='coerce')
            df_data = df_data[df_data['rating_cleaned'] >= min_rating]

        if df_data.empty:
            return json.dumps({"status": "ok", "restaurants": []})

        available_restaurants = df_avail[df_avail[valid_slots_to_check].sum(axis=1) > 0]['Name']
        final_list = df_data[df_data['name'].isin(available_restaurants)]
        
        output_cols = ['name', 'location', 'cuisines', 'approx_cost(for two people)', 'rate']
        result = final_list[output_cols].to_dict('records')
        
        return json.dumps({"status": "ok", "restaurants": result})

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_restaurant_details(date: str, restaurant_name: str) -> str:
    """Implementation for get_restaurant_details tool."""
    try:
        validator = Validator()
        valid_slots_to_check, error = validator.get_valid_time_slots(date)
        if error:
            return json.dumps({"status": "ok", "details": {"available_slots": [], "message": error}})

        df_data = data_manager.get_restaurant_data()
        df_avail = data_manager.get_availability(date)
        
        details = df_data[df_data['name'] == restaurant_name]
        availability = df_avail[df_avail['Name'] == restaurant_name]

        if details.empty:
            return json.dumps({"status": "error", "message": "Restaurant not found."})
        if availability.empty:
            return json.dumps({"status": "error", "message": "Restaurant not found in tracker."})

        details_dict = details.iloc[0].to_dict()
        avail_dict = availability.iloc[0]
        available_slots = []
        
        for slot in valid_slots_to_check:
            if avail_dict[slot] > 0:
                available_slots.append({"time_slot": slot, "tables_available": int(avail_dict[slot])})
        
        result = {
            "name": details_dict.get("name"),
            "location": details_dict.get("location"),
            "address": details_dict.get("address"),
            "cuisines": details_dict.get("cuisines"),
            "approx_cost(for two people)": details_dict.get("approx_cost(for two people)"),
            "rate": details_dict.get("rate"),
            "menu_item": details_dict.get("menu_item"),
            "max_party_size": details_dict.get("party_size"),
            "available_slots": available_slots
        }
        return json.dumps({"status": "ok", "details": result})
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def book_table(date: str, restaurant_name: str, time_slot: str, party_size: int, customer_name: str, customer_email: str, customer_phone: str, special_requests: str = None) -> str:
    """Implementation for book_table tool."""
    try:
        df_data = data_manager.get_restaurant_data()
        restaurant_info = df_data[df_data['name'] == restaurant_name]
        if restaurant_info.empty:
            return json.dumps({"status": "error", "message": f"Restaurant '{restaurant_name}' not found."})
        
        max_size = restaurant_info.iloc[0]['party_size']
        if party_size > max_size:
            return json.dumps({"status": "error", "message": f"Party size {party_size} exceeds the maximum of {max_size} for this restaurant."})

        tables_needed = data_manager.calculate_tables_needed(party_size)
        df_avail = data_manager.get_availability(date)
        restaurant_avail = df_avail[df_avail['Name'] == restaurant_name]
        
        if restaurant_avail.empty:
            return json.dumps({"status": "error", "message": f"Restaurant '{restaurant_name}' not found in tracker."})
            
        tables_available = restaurant_avail.iloc[0][time_slot]
        
        if tables_available < tables_needed:
            return json.dumps({"status": "error", "message": f"Not enough tables. Requested {tables_needed} (for {party_size} guests), but only {tables_available} available at {time_slot}."})

        success = data_manager.update_availability(date, restaurant_name, time_slot, -tables_needed)
        if not success:
            return json.dumps({"status": "error", "message": "Failed to update availability tracker."})
        
        booking_details = {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "restaurant_name": restaurant_name,
            "restaurant_address": restaurant_info.iloc[0]['address'],
            "party_size": party_size,
            "time_slot": time_slot,
            "special_requests": special_requests
        }
        new_booking = data_manager.add_booking(date, booking_details)
        
        return json.dumps({"status": "confirmed", "booking_details": new_booking})

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def find_bookings(date: str, booking_id: str = None, customer_name: str = None, customer_email: str = None, customer_phone: str = None) -> str:
    """Implementation for find_bookings tool."""
    try:
        df_bookings = data_manager.get_bookings(date)
        if df_bookings.empty:
            return json.dumps({"status": "ok", "bookings": []})

        if booking_id:
            result_df = df_bookings[df_bookings['booking_id'] == booking_id]
        elif customer_name and customer_email and customer_phone:
            result_df = df_bookings[
                (df_bookings['customer_name'].str.lower() == customer_name.lower()) &
                (df_bookings['customer_email'].str.lower() == customer_email.lower()) &
                (df_bookings['customer_phone'] == customer_phone)
            ]
        else:
            return json.dumps({"status": "error", "message": "You must provide either a booking_id or all three (name, email, phone) to search."})
        
        return json.dumps({"status": "ok", "bookings": result_df.to_dict('records')})

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def cancel_booking(date: str, booking_id: str) -> str:
    """Implementation for cancel_booking tool."""
    try:
        df_bookings = data_manager.get_bookings(date)
        booking = df_bookings[df_bookings['booking_id'] == booking_id]
        
        if booking.empty:
            return json.dumps({"status": "error", "message": "Booking ID not found."})
            
        booking = booking.iloc[0]
        
        if booking['status'] == 'cancelled':
            return json.dumps({"status": "error", "message": "This booking is already cancelled."})

        # We can do a simple validation here
        validator = Validator()
        is_valid, error_msg, book_date_obj = validator._validate_date_window(date)
        if is_valid: # Only check time if date is valid
            is_valid_time, time_err = validator._validate_time_rules(book_date_obj, booking['time_slot'])
            if not is_valid_time:
                return json.dumps({"status": "error", "message": f"Cannot cancel: {time_err}"})

        tables_to_add_back = booking['tables_reserved']
        restaurant_name = booking['restaurant_name']
        time_slot = booking['time_slot']
        
        success = data_manager.update_availability(date, restaurant_name, time_slot, tables_to_add_back)
        if not success:
            return json.dumps({"status": "error", "message": "Failed to add tables back to tracker. Cancellation aborted."})

        success = data_manager.update_booking_status(date, booking_id, "cancelled")
        if not success:
            return json.dumps({"status": "error", "message": "Tables were added back, but failed to update booking status log."})

        return json.dumps({"status": "ok", "message": f"Booking {booking_id} has been successfully cancelled."})

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# --- Tool Mapping (Program Layer) ---
tool_functions = {
    "get_available_restaurants": get_available_restaurants,
    "get_restaurant_details": get_restaurant_details,
    "book_table": book_table,
    "find_bookings": find_bookings,
    "cancel_booking": cancel_booking,
}