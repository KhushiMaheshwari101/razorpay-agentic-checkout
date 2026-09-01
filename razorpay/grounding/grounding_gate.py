"""
Grounding Gate – verifies agent cart items and price claims against 
the verified catalog metadata to prevent AI hallucinations, price tampering, and type crashes.
"""

from typing import Dict, Any, List
import math

def verify_cart_grounding(cart_items: Any, catalog_database: Any) -> Dict[str, Any]:
    """
    Validates every item in the cart against the source-of-truth catalog database.
    Checks for exact item existence, price matching, stock availability, and safe type coercion.
    """
    discrepancies = []
    verified_items = []

    # Safe input type validation
    if not isinstance(catalog_database, list):
        return {
            "is_grounded": False,
            "verified_items": [],
            "discrepancies": ["Invalid catalog database format provided."]
        }

    if not isinstance(cart_items, list):
        return {
            "is_grounded": False,
            "verified_items": [],
            "discrepancies": ["Invalid cart items format provided."]
        }

    # Build a fast lookup dictionary from the catalog
    catalog_lookup = {}
    for entry in catalog_database:
        if isinstance(entry, dict) and "id" in entry:
            catalog_lookup[entry["id"]] = entry

    for cart_item in cart_items:
        if not isinstance(cart_item, dict):
            discrepancies.append("Malformed cart item entry: Expected dictionary.")
            continue

        item_id = cart_item.get("id")
        if not item_id or item_id not in catalog_lookup:
            discrepancies.append(f"Hallucination / Invalid Item: Item ID '{item_id}' does not exist in the official catalog.")
            continue

        # Safe type conversion for price and quantity to prevent crashes
        try:
            claimed_price = float(cart_item.get("price", 0.0))
            claimed_qty = int(cart_item.get("quantity", 1))
        except (ValueError, TypeError):
            discrepancies.append(f"Type validation error for item '{item_id}': Price or quantity must be numeric.")
            continue

        # Negative quantity check
        if claimed_qty <= 0:
            discrepancies.append(f"Invalid quantity for item '{item_id}': Quantity must be greater than zero.")
            continue

        catalog_entry = catalog_lookup[item_id]
        
        try:
            actual_price = float(catalog_entry.get("price", 0.0))
        except (ValueError, TypeError):
            discrepancies.append(f"Catalog data error: Invalid price format for catalog item '{item_id}'.")
            continue

        stock_status = bool(catalog_entry.get("in_stock", True))

        # Safe floating-point price comparison
        if not math.isclose(claimed_price, actual_price, rel_tol=1e-9, abs_tol=1e-9):
            discrepancies.append(
                f"Price tampering detected for '{item_id}': Claimed price ({claimed_price}) does not match catalog price ({actual_price})."
            )

        # Stock availability check
        if not stock_status:
            discrepancies.append(f"Stock failure: Item '{item_id}' is currently out of stock.")

        verified_items.append({
            "id": item_id,
            "name": catalog_entry.get("name", "Unknown Product"),
            "unit_price": actual_price,
            "quantity": claimed_qty,
            "total_price": actual_price * claimed_qty
        })

    is_grounded = len(discrepancies) == 0

    return {
        "is_grounded": is_grounded,
        "verified_items": verified_items,
        "discrepancies": discrepancies
    }


if __name__ == "__main__":
    mock_catalog = [
        {"id": "prod_esp32", "name": "ESP32 Dev Board", "price": 499.0, "in_stock": True},
        {"id": "prod_sensor", "name": "MPU6050 Gyro", "price": 299.0, "in_stock": False}
    ]

    print("--- Testing Grounding Gate ---")
    
    # Test 1: Valid cart
    cart_valid = [{"id": "prod_esp32", "price": 499.0, "quantity": 1}]
    print(f"Test 1 (Valid Cart): {verify_cart_grounding(cart_valid, mock_catalog)}")

    # Test 2: Price Tampering / Hallucination
    cart_tampered = [{"id": "prod_esp32", "price": 10.0, "quantity": 1}]
    print(f"Test 2 (Price Tampering): {verify_cart_grounding(cart_tampered, mock_catalog)}")

    # Test 3: Malformed / Non-numeric type injection
    cart_malformed = [{"id": "prod_esp32", "price": "free", "quantity": 2}]
    print(f"Test 3 (Malformed Type Injection): {verify_cart_grounding(cart_malformed, mock_catalog)}")