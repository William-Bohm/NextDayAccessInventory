import requests
import json
from getterFunctions import fetch_quotes, fetch_jobs, get_job_count, get_quote_count, fetch_jobs_all_data
from queryCost import log_query_cost
from config import CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN

import pprint


def look_at_all_data():
    print("Getting access token...")
    token_data = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
    access_token = token_data["access_token"]
    
    # Initialize variables
    cursor = None
    all_jobs = []
    
    # Open a file to save the results
    with open("job_results.txt", "w") as f:
        f.write("Job Batches Results\n")
        f.write("==================\n\n")
    
    # Loop 10 times to get 5 jobs each time
    for i in range(10):
        print(f"Fetching batch {i+1}/10...")
        
        # Fetch jobs using the cursor from previous batch
        page_data = fetch_jobs_all_data(access_token, after=cursor, limit=5)
        
        # Save this batch data to file
        with open("job_results.txt", "a") as f:
            f.write(f"\n\n--- BATCH {i+1} ---\n")
            f.write(pprint.pformat(page_data))
            f.write("\n--------------\n")
        
        if "data" not in page_data or "jobs" not in page_data["data"]:
            print("Error fetching jobs data")
            break
            
        # Extract the jobs from this batch
        batch_jobs = page_data["data"]["jobs"]["nodes"]
        all_jobs.extend(batch_jobs)
        
        # Print how many jobs we got in this batch
        print(f"Retrieved {len(batch_jobs)} jobs in this batch")
        
        # Check if there are more jobs to fetch
        if not page_data["data"]["jobs"]["pageInfo"]["hasNextPage"]:
            print("No more jobs to fetch")
            break
            
        # Update cursor for next batch
        cursor = page_data["data"]["jobs"]["pageInfo"]["endCursor"]
        
        # Add a small delay to avoid rate limiting (optional)
        import time
        time.sleep(0.5)
    
    print(f"Total jobs fetched: {len(all_jobs)}")
    
    # Save summary to file
    with open("job_results.txt", "a") as f:
        f.write("\n\nSUMMARY\n")
        f.write("=======\n")
        f.write(f"Total jobs fetched: {len(all_jobs)}\n\n")
        
        # Save all job IDs and titles
        for i, job in enumerate(all_jobs):
            job_info = f"Job {i+1}: ID {job['id']}, Title: {job.get('title', 'No title')}"
            f.write(job_info + "\n")
            print(job_info)

def get_access_token(client_id, client_secret, refresh_token):
    """Get a new access token using the refresh token"""
    token_url = "https://api.getjobber.com/api/oauth/token"
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    response = requests.post(token_url, data=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get access token: {response.text}")

class InventoryItem:
    def __init__(self, name=None, sku=None, description=None, source_location=None, category=None):
        self.name = name
        self.sku = sku
        self.description = description
        self.source_location = source_location
        self.category = category
    
    def __str__(self):
        return f"Name: {self.name}, SKU: {self.sku}, Description: {self.description}"

def extract_sku_from_name(name):
    """
    Attempt to extract SKU-like patterns from product names.
    Common patterns include PS###WR, BL###WR, etc.
    """
    if not name:
        return None
    
    # Look for common SKU patterns
    import re
    
    # Match patterns like PS636WR, BL342WR, RAEZ0110, etc.
    sku_pattern = re.compile(r'\b([A-Z]{2,}\d+[A-Z0-9]*)\b')
    match = sku_pattern.search(name)
    
    if match:
        return match.group(1)
    return None

def remove_sku_from_name(name, sku):
    """
    Remove the SKU from the name string if it exists.
    """
    if not name or not sku:
        return name
    
    # Create a pattern that matches the SKU with optional surrounding characters
    # This handles cases like "PS636WR - Description" or "Description (PS636WR)"
    import re
    patterns = [
        rf'\b{re.escape(sku)}\b\s*[-:]\s*',  # "SKU - " or "SKU: "
        rf'\s*[-:]\s*\b{re.escape(sku)}\b',  # " - SKU" or ": SKU"
        rf'\s*\({re.escape(sku)}\)\s*',      # " (SKU) "
        rf'\b{re.escape(sku)}\b\s*,\s*',     # "SKU, " 
        rf'\s*\b{re.escape(sku)}\b,?\s*',    # Just the SKU with spaces, optionally followed by comma
    ]
    
    result = name
    for pattern in patterns:
        result = re.sub(pattern, ' ', result)
    
    # Clean up extra whitespace and ensure no leading/trailing spaces
    result = re.sub(r'\s+', ' ', result).strip()
    
    # One final check for any trailing commas and clean them up
    if result.endswith(','):
        result = result[:-1].strip()
    
    return result

def process_job_inventory(job):
    """
    Process a single job and extract only PRODUCT inventory items with their details.
    """
    inventory_items = []
    
    # Check if the job has line items
    if 'lineItems' not in job or 'nodes' not in job['lineItems']:
        return inventory_items
    
    for line_item in job['lineItems']['nodes']:
        # Track where we found the data
        source_locations = []
        
        # Initialize an inventory item
        item = InventoryItem()
        
        # Check if this is a PRODUCT (either directly or in linked item)
        is_product = False
        
        if 'category' in line_item and line_item['category'] == 'PRODUCT':
            is_product = True
            item.category = 'PRODUCT'
            source_locations.append('lineItem.category')
        
        # Check linked product/service category
        if 'linkedProductOrService' in line_item and line_item['linkedProductOrService']:
            linked_item = line_item['linkedProductOrService']
            if 'category' in linked_item and linked_item['category'] == 'PRODUCT':
                is_product = True
                item.category = 'PRODUCT'
                source_locations.append('linkedProductOrService.category')
        
        # Skip if this is not a product
        if not is_product:
            continue

        if 'description' in line_item and line_item['description']:
            item.description = line_item['description']
            source_locations.append('lineItem.description')
        
        # Extract data from direct line item
        if 'name' in line_item and line_item['name']:
            source_locations.append('lineItem.name')
            # Try to extract SKU from name
            item.sku = extract_sku_from_name(line_item['name'])
            if item.sku is not None and item.description is not None:
                item.name = item.description
                # Remove SKU from name if it exists
                item.name = remove_sku_from_name(item.name, item.sku)
            else:
                item.name = line_item['name']
            
        # If there's a linked product/service, check it for more info
        if 'linkedProductOrService' in line_item and line_item['linkedProductOrService']:
            linked_item = line_item['linkedProductOrService']
            
            # If we didn't get a name from the line item, or the linked item has a different name
            if ('name' in linked_item and linked_item['name'] and 
                (not item.name or linked_item['name'] != item.name)):
                source_locations.append('linkedProductOrService.name')
                # Try to extract SKU from name if we don't have one yet
                if not item.sku:
                    item.sku = extract_sku_from_name(linked_item['name'])
                    if item.sku is not None and item.description is not None:
                        item.name = item.description
                        # Remove SKU from name if it exists
                        item.name = remove_sku_from_name(item.name, item.sku)
                    else:
                        item.name = linked_item['name']
            
            # If we didn't get a description, or the linked item has additional description
            if ('description' in linked_item and linked_item['description'] and 
                (not item.description or linked_item['description'] != item.description)):
                item.description = linked_item['description']
                source_locations.append('linkedProductOrService.description')
        
        # Record where we found the data
        item.source_location = ', '.join(source_locations)
        
        # Add to our list if we have at least a name
        if item.name:
            inventory_items.append(item)
    
    return inventory_items

def aggregate_inventory_by_name(inventory_items):
    """
    Aggregate inventory items by unique name-SKU combinations and count occurrences.
    
    Args:
        inventory_items (list): List of InventoryItem objects
        
    Returns:
        list: List of dictionaries containing name, SKU, and count, sorted by count in descending order
    """
    if not inventory_items:
        return []
    
    # Create a dictionary to count occurrences of each name-SKU combination
    item_counts = {}
    
    for item in inventory_items:
        # Create a composite key using both name and SKU
        # If SKU is None, use an empty string to avoid None-related issues
        name = item.name if item.name else ""
        sku = item.sku if item.sku else ""
        key = (name, sku)
        
        # Increment the count for this name-SKU combination
        item_counts[key] = item_counts.get(key, 0) + 1
    
    # Convert to a list of dictionaries with name, SKU, and count
    result = []
    for (name, sku), count in item_counts.items():
        result.append({
            "name": name,
            "sku": sku,
            "count": count
        })
    
    # Sort by count in descending order
    result.sort(key=lambda x: x["count"], reverse=True)
    
    return result

def print_inventory_items(inventory_items):
    
    """
    Print inventory items and metadata
    """
    # Track items without SKUs for further analysis
    items_without_sku = []
    
    # Print all inventory items
    print("\n=== INVENTORY ITEMS FOUND ===")
    for idx, item in enumerate(inventory_items, 1):
        print(f"{idx}. {item}")
        
        # Collect items without SKUs
        if not item.sku:
            items_without_sku.append(item)
    
    # Analyze and print metadata
    print("\n=== INVENTORY METADATA ===")
    print(f"Total inventory items found: {len(inventory_items)}")
    
    # Handle case where no inventory items were found
    if len(inventory_items) > 0:
        # Count items with names, SKUs, descriptions
        with_names = sum(1 for item in inventory_items if item.name)
        with_skus = sum(1 for item in inventory_items if item.sku)
        with_descriptions = sum(1 for item in inventory_items if item.description)
        
        print(f"Items with names: {with_names} ({with_names/len(inventory_items)*100:.1f}%)")
        print(f"Items with SKUs: {with_skus} ({with_skus/len(inventory_items)*100:.1f}%)")
        print(f"Items with descriptions: {with_descriptions} ({with_descriptions/len(inventory_items)*100:.1f}%)")
        
        # Analyze data source locations
        source_locations = {}
        for item in inventory_items:
            for source in item.source_location.split(', '):
                source_locations[source] = source_locations.get(source, 0) + 1
                
        print("\n=== DATA SOURCE DISTRIBUTION ===")
        for source, count in sorted(source_locations.items(), key=lambda x: x[1], reverse=True):
            print(f"{source}: {count} ({count/len(inventory_items)*100:.1f}%)")
        
        # Print detailed information about items without SKUs
        print("\n=== ITEMS WITHOUT SKU ===")
        print(f"Found {len(items_without_sku)} items without SKUs ({len(items_without_sku)/len(inventory_items)*100:.1f}% of total)")
        
        # Save the detailed information to a file for further analysis
        with open("items_without_sku.txt", "w") as f:
            f.write(f"Total items without SKU: {len(items_without_sku)}\n\n")
            
            for idx, item in enumerate(items_without_sku, 1):
                f.write(f"Item #{idx}:\n")
                f.write(f"  Name: {item.name}\n")
                f.write(f"  Description: {item.description}\n")
                f.write(f"  Category: {item.category}\n")
                f.write(f"  Source: {item.source_location}\n")
                f.write("\n")
                
                # Also print first 10 items to console for immediate review
                if idx <= 10:
                    print(f"\nItem #{idx}:")
                    print(f"  Name: {item.name}")
                    print(f"  Description: {item.description}")
                    print(f"  Category: {item.category}")
                    print(f"  Source: {item.source_location}")
        
        print(f"\nDetailed information for all {len(items_without_sku)} items without SKUs has been saved to 'items_without_sku.txt'")
    else:
        print("No inventory items found in the jobs.")



def get_all_jobs(access_token):
            # Initialize variables for pagination
        cursor = None
        has_next_page = True
        all_jobs = []
        batch_count = 0
        
        # Import time for sleep functionality
        import time
        
        # Loop until we've fetched all jobs
        while has_next_page:
            batch_count += 1
            print(f"\nFetching batch {batch_count} of jobs...")
            
            # Fetch 5 jobs at a time using cursor-based pagination
            jobs_data = fetch_jobs(access_token, after=cursor, limit=5)
            
            # Extract jobs from this batch
            batch_jobs = jobs_data["data"]["jobs"]["nodes"]
            all_jobs.extend(batch_jobs)
            
            # Get pagination info for next batch
            pagination_info = jobs_data["data"]["jobs"]["pageInfo"]
            cursor = pagination_info["endCursor"]
            has_next_page = pagination_info["hasNextPage"]
            
            print(f"Retrieved {len(batch_jobs)} jobs in this batch")
            print(f"Total jobs fetched so far: {len(all_jobs)}")
            
            if has_next_page:
                print("Sleeping for 1 second before next batch...")
                time.sleep(1)
            else:
                print("No more jobs to fetch.")
        
        # Process all jobs to extract inventory information
        all_inventory_items = []
        
        for job in all_jobs:
            job_inventory = process_job_inventory(job)
            all_inventory_items.extend(job_inventory)
        
        return all_inventory_items

def main():
    try:
        print("Getting access token...")
        token_data = get_access_token(CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        access_token = token_data["access_token"]
        print("Access token obtained successfully")
        
        if "refresh_token" in token_data:
            new_refresh_token = token_data["refresh_token"]
            print("New refresh token received - save this for future use")
        
        all_inventory_items = get_all_jobs(access_token)

        # Print aggregated inventory by name
        name_counts = aggregate_inventory_by_name(all_inventory_items)
        pprint.pprint(name_counts)

                
    except Exception as e:
        print(f"Error: {str(e)}")
            
        
if __name__ == "__main__":
    main()