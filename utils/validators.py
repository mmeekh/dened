def validate_trc20_address(address: str) -> bool:
    """Validate TRC20 wallet address format"""
    if not isinstance(address, str):
        return False
    
    # Basic TRC20 address validation
    if not address.startswith('T'):
        return False
        
    if len(address) != 34:
        return False
        
    # Check if address contains only valid characters
    valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
    if not all(c in valid_chars for c in address[1:]):
        return False
        
    return True