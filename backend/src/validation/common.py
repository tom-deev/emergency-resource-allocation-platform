def validate_coordinates(latitude: float, longitude: float) -> None:
    """
    Validate geographic latitude and longitude values.
    """

    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")

    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")