import re

def validate_name(name):
    if not name:
        return "Name cannot be empty."
    if not re.match(r'^[A-Z][A-Za-z\s]{2,}$', name):
        return "Name can only contain letters and spaces."
    return None
def validate_phone(phone):
    if not phone:
        return "Phone number cannot be empty."
    if not re.match(r'^\d{10}$', phone):
        return "Phone number must be 10 digits."
    return None