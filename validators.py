import json
from datetime import datetime, timedelta
import data_manager

class Validator:
    """
    This class is the 'C' (Controller) layer.
    It contains all deterministic business logic.
    """
    
    def __init__(self):
        self.time_slots = data_manager.TIME_SLOTS

    def _validate_date_window(self, date_str: str) -> (bool, str, datetime.date):
        """Checks the 72-hour (0-3 days) booking window."""
        try:
            book_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            return False, "Invalid date format. Please use DD.MM.YYYY.", None

        today = datetime.now().date()
        max_date = today + timedelta(days=3)

        if not (today <= book_date <= max_date):
            msg = f"Bookings are only allowed from today ({today.strftime('%d.%m.%Y')}) up to 3 days in advance ({max_date.strftime('%d.%m.%Y')})."
            return False, msg, None
        
        return True, "", book_date

    def _validate_time_rules(self, book_date_obj: datetime.date, time_slot: str) -> (bool, str):
        """Checks the 'past time' and '30-minute' rules."""
        try:
            book_time = datetime.strptime(time_slot, "%I:%M %p").time()
            booking_datetime = datetime.combine(book_date_obj, book_time)
            
            now = datetime.now()
            
            # Check 1: Is the time in the past?
            if booking_datetime < now:
                return False, f"The time slot {time_slot} on {book_date_obj.strftime('%d.%m.%Y')} is in the past. Please select a future time."

            # Check 2: Is it within the 30-minute buffer?
            min_booking_time = now + timedelta(minutes=30)
            if booking_datetime < min_booking_time:
                return False, f"Bookings must be made at least 30 minutes in advance. The earliest time you can book for is around {min_booking_time.strftime('%I:%M %p')}."
                
            return True, ""
            
        except Exception as e:
            return False, f"Error parsing time slot: {e}"

    def get_valid_time_slots(self, date_str: str) -> (list[str], str):
        """
        Gets all future, bookable time slots for a given date.
        This is used by recommendation tools.
        """
        is_valid, error_msg, book_date_obj = self._validate_date_window(date_str)
        if not is_valid:
            return [], error_msg

        if book_date_obj > datetime.now().date():
            return self.time_slots, "" # All slots are valid for a future date

        # If it's for today, we must filter
        valid_slots = []
        now = datetime.now()
        min_booking_time = now + timedelta(minutes=30)
        
        for slot_str in self.time_slots:
            try:
                slot_time = datetime.strptime(slot_str, "%I:%M %p").time()
                slot_datetime = datetime.combine(book_date_obj, slot_time)
                
                if slot_datetime >= min_booking_time:
                    valid_slots.append(slot_str)
            except Exception:
                continue 
                
        if not valid_slots:
            return [], "All available time slots for today are in the past or within the next 30 minutes."

        return valid_slots, ""

    def validate_tool_call(self, tool_name: str, args: dict) -> (bool, str):
        """
        A single validation function for the Controller to call.
        It routes to the correct internal validation logic.
        """
        date_str = args.get("date")
        if not date_str:
             # A date is required for all our tools
            return False, "The agent plan is invalid: 'date' is a required argument for all tools."
        
        # 1. Validate the date for ALL tools
        is_valid_date, error_msg, book_date_obj = self._validate_date_window(date_str)
        if not is_valid_date:
            return False, error_msg
        
        # 2. If the tool needs a time_slot, validate it
        time_slot = args.get("time_slot")
        if tool_name == "book_table" and time_slot:
            is_valid_time, time_err = self._validate_time_rules(book_date_obj, time_slot)
            if not is_valid_time:
                return False, time_err
        
        # 3. If cancelling, check if it's too late
        if tool_name == "cancel_booking":
            # This is a bit trickier. We need to find the booking first to get its time.
            # We'll let this pass for now, and the tool itself will fail.
            # A more advanced version would have the tool call `find_bookings` first.
            pass

        return True, ""