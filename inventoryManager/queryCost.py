def extract_query_cost(response_data):
    """
    Extract query cost information from a GraphQL response.
    
    Args:
        response_data (dict): The JSON response from a GraphQL query
        
    Returns:
        dict: A dictionary containing cost information or None if not available
    """
    if not isinstance(response_data, dict):
        return None
        
    # Check if the extensions and cost information exist in the response
    if 'extensions' in response_data and 'cost' in response_data['extensions']:
        cost_info = response_data['extensions']['cost']
        
        # Create a structured object with cost information
        cost_data = {
            'requested_cost': cost_info.get('requestedQueryCost', 0),
            'actual_cost': cost_info.get('actualQueryCost', 0),
            'throttle_status': {
                'maximum_available': cost_info.get('throttleStatus', {}).get('maximumAvailable', 0),
                'currently_available': cost_info.get('throttleStatus', {}).get('currentlyAvailable', 0),
                'restore_rate': cost_info.get('throttleStatus', {}).get('restoreRate', 0),
                'percentage_used': 0  # Will be calculated below
            }
        }
        
        # Calculate percentage of available points used by this query
        max_available = cost_data['throttle_status']['maximum_available']
        if max_available > 0:
            currently_available = cost_data['throttle_status']['currently_available']
            percentage_used = ((max_available - currently_available) / max_available) * 100
            cost_data['throttle_status']['percentage_used'] = round(percentage_used, 2)
            
        return cost_data
    
    # Handle the case where we got an error response with throttling information
    if 'errors' in response_data and 'extensions' in response_data and 'cost' in response_data['extensions']:
        # This is a throttled response
        cost_info = response_data['extensions']['cost']
        
        return {
            'is_throttled': True,
            'requested_cost': cost_info.get('requestedQueryCost', 0),
            'throttle_status': {
                'maximum_available': cost_info.get('throttleStatus', {}).get('maximumAvailable', 0),
                'currently_available': cost_info.get('throttleStatus', {}).get('currentlyAvailable', 0),
                'restore_rate': cost_info.get('throttleStatus', {}).get('restoreRate', 0)
            }
        }
    
    return None

def log_query_cost(response_data, query_name="Unknown query"):
    """
    Log query cost information in a readable format.
    
    Args:
        response_data (dict): The JSON response from a GraphQL query
        query_name (str): Name of the query for identification in logs
    """
    cost_data = extract_query_cost(response_data)
    
    if not cost_data:
        print(f"No cost information available for {query_name}")
        return
    
    if cost_data.get('is_throttled', False):
        print(f"⚠️ THROTTLED REQUEST: {query_name}")
        print(f"  Requested cost: {cost_data['requested_cost']} points")
        print(f"  Maximum available: {cost_data['throttle_status']['maximum_available']} points")
        print(f"  Currently available: {cost_data['throttle_status']['currently_available']} points")
        print(f"  Restore rate: {cost_data['throttle_status']['restore_rate']} points/second")
        
        # Calculate how long to wait before trying again
        points_needed = cost_data['requested_cost']
        available_points = cost_data['throttle_status']['currently_available']
        restore_rate = cost_data['throttle_status']['restore_rate']
        
        if restore_rate > 0 and points_needed > available_points:
            wait_time = (points_needed - available_points) / restore_rate
            print(f"  Suggested wait time before retry: {wait_time:.2f} seconds")
    else:
        print(f"✅ QUERY COST: {query_name}")
        print(f"  Requested cost: {cost_data['requested_cost']} points")
        print(f"  Actual cost: {cost_data['actual_cost']} points")
        print(f"  Currently available: {cost_data['throttle_status']['currently_available']} " +
              f"of {cost_data['throttle_status']['maximum_available']} points " +
              f"({cost_data['throttle_status']['percentage_used']}% used)")
        print(f"  Restore rate: {cost_data['throttle_status']['restore_rate']} points/second")
