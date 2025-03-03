import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from time import sleep
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('GoogleSheetsManager')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Constants
SHEET_NAME = "Inventory"
# Define row offset for headers - adjust this value to add more rows for metadata at the top
HEADER_ROW_OFFSET = 5  # This means headers will start at row 5, leaving rows 1-4 for metadata
COLUMN_HEADERS = [
    "Part",
    "Part No.",
    "Description",
    "Current Inv",
    "Quote QTY",
    "Job QTY",
    "Total allocated",
    "Available QTY"
]
logger.debug(f"Using sheet name: {SHEET_NAME}")
logger.debug(f"Column headers: {COLUMN_HEADERS}")

def get_google_sheets_client():
    """Initialize and return a Google Sheets client."""
    logger.info("Initializing Google Sheets client")
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Get the absolute path to the credentials file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(current_dir, 'nextdayaccess-452516-a51a5b7a02b8.json')
    
    logger.debug(f"Using credentials file at: {creds_path}")
    
    # Authenticate using the service account credentials
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        logger.info("Credentials loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}", exc_info=True)
        raise
    
    # Return the client
    logger.info("Google Sheets client initialized successfully")
    return gspread.authorize(creds)

def refresh_auth_if_needed(func):
    """Decorator to refresh auth token if needed."""
    def wrapper(*args, **kwargs):
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                if ("invalid_grant" in str(e) or "expired" in str(e)) and retry_count < max_retries - 1:
                    logger.warning("Auth token expired, refreshing...")
                    retry_count += 1
                    sleep(1)  # Small delay before retry
                else:
                    logger.error(f"API error: {e}")
                    raise
    
    return wrapper

def initialize_sheet(client, sheet_id):
    """Ensure the sheet exists with the correct column headers."""
    logger.info(f"Initializing sheet with ID: {sheet_id}")
    try:
        # Open the spreadsheet
        spreadsheet = client.open_by_key(sheet_id)
        logger.debug(f"Opened spreadsheet: {spreadsheet.title}")
        
        # Check if the inventory sheet exists, create it if it doesn't
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
            logger.debug(f"Found existing worksheet: {SHEET_NAME}")
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Worksheet '{SHEET_NAME}' not found, creating it")
            # Create with more rows to accommodate the offset
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows=HEADER_ROW_OFFSET + 100, cols=len(COLUMN_HEADERS))
        
        # Get the current headers from the offset row
        try:
            current_headers = worksheet.row_values(HEADER_ROW_OFFSET)
            logger.debug(f"Current headers at row {HEADER_ROW_OFFSET}: {current_headers}")
            
            # If the headers don't match, set them up
            if not current_headers or current_headers != COLUMN_HEADERS:
                logger.info(f"Headers at row {HEADER_ROW_OFFSET} missing or don't match, setting up headers")
                # Only clear from the header row down
                cell_range = f"{HEADER_ROW_OFFSET}:{worksheet.row_count}"
                worksheet.batch_clear([cell_range])
                # Write headers at the offset row - using proper cell reference for update
                cell_ref = f"A{HEADER_ROW_OFFSET}"
                worksheet.update(cell_ref, [COLUMN_HEADERS])
                logger.debug(f"Updated headers at {cell_ref}")
        except Exception as e:
            # Either empty or headers not set up
            logger.info(f"Setting up headers at row {HEADER_ROW_OFFSET}: {str(e)}")
            cell_ref = f"A{HEADER_ROW_OFFSET}"
            worksheet.update(cell_ref, [COLUMN_HEADERS])
            logger.debug(f"Updated headers at {cell_ref}")
            
        logger.info("Sheet initialization complete")
        return worksheet
        
    except Exception as e:
        logger.error(f"Error initializing sheet: {e}")
        return None

@refresh_auth_if_needed
def upload_inventory_data(data):
    """
    Upload inventory data to Google Sheets.
    
    Args:
        data: List of dictionaries with keys 'name', 'sku', 'quotes_count', 'jobs_count', 'description'
    
    Returns:
        Boolean indicating success or failure
    """
    logger.info(f"Starting upload of {len(data)} inventory items")
    try:
        # Get sheet ID from environment
        sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        if not sheet_id:
            logger.error("GOOGLE_SHEETS_ID not found in environment variables")
            raise ValueError("GOOGLE_SHEETS_ID not found in environment variables")
        
        # Initialize client and sheet
        client = get_google_sheets_client()
        worksheet = initialize_sheet(client, sheet_id)
        
        if not worksheet:
            logger.error("Failed to initialize worksheet")
            return False
        
        # Update cell B1 with the current date and time - fixed to use 2D array format
        current_time = datetime.now()
        # Format as "June 20, 9:06 am" - no year, more readable format
        friendly_time = current_time.strftime("%B %-d, %-I:%M %p").replace("AM", "am").replace("PM", "pm")
        worksheet.update('B1', [[f"{friendly_time}"]])  # This requires a 2D array
        logger.info(f"Updated timestamp in cell B1: Last Updated: {friendly_time}")
        
        # Get all current data from the sheet, starting at the header row offset
        logger.info("Fetching current sheet data")
        all_values = worksheet.get_all_values()[HEADER_ROW_OFFSET-1:]  # Adjust index to be 0-based
        
        if not all_values or len(all_values) < 1:
            # Sheet is empty or only has headers
            logger.info("Sheet data area is empty, ensuring headers are present")
            worksheet.update(f"{HEADER_ROW_OFFSET}:1", [COLUMN_HEADERS])
            all_values = [COLUMN_HEADERS]
        
        headers = all_values[0]
        logger.debug(f"Headers found: {headers}")
        
        # Create indices for important columns
        try:
            name_idx = headers.index("Part")
            sku_idx = headers.index("Part No.")
            description_idx = headers.index("Description")
            quote_idx = headers.index("Quote QTY")
            job_idx = headers.index("Job QTY")
            logger.debug(f"Column indices - Name: {name_idx}, SKU: {sku_idx}, Description: {description_idx}, Quote: {quote_idx}, Job: {job_idx}")
        except ValueError as e:
            logger.error(f"Column header error: {e}")
            return False
        
        # Create a mapping of existing rows for quick lookup
        # Key: (name, sku), Value: row_index
        existing_rows = {}
        for i, row in enumerate(all_values[1:], start=2):  # Start from 2 as 1 is header
            if len(row) > max(name_idx, sku_idx):  # Ensure row has enough columns
                name_val = row[name_idx] if name_idx < len(row) else ""
                sku_val = row[sku_idx] if sku_idx < len(row) else ""
                key = (name_val, sku_val)
                existing_rows[key] = i
        
        logger.info(f"Found {len(existing_rows)} existing items in spreadsheet")
        
        # Process each item in our data
        processed_keys = set()
        cells_to_update = []  # List to hold all cell updates
        new_rows = []  # List to hold new rows to be added
        
        # Prepare and collect all the updates
        logger.info("Processing inventory data")
        for item in data:
            name = item['name']
            sku = item['sku']
            quotes_count = item['quotes_count']
            jobs_count = item['jobs_count']
            description = item.get('description', '')  # Get description, default to empty string if not present
            
            key = (name, sku)
            processed_keys.add(key)
            
            if key in existing_rows:
                # Update existing row - adjust the row number to account for header offset
                row_num = existing_rows[key] + HEADER_ROW_OFFSET - 1  # -1 because headers are now at index 0 in all_values
                cells_to_update.append(gspread.Cell(row=row_num, col=quote_idx+1, value=quotes_count))
                cells_to_update.append(gspread.Cell(row=row_num, col=job_idx+1, value=jobs_count))
                cells_to_update.append(gspread.Cell(row=row_num, col=description_idx+1, value=description))
                logger.debug(f"Updating existing item: {name} (SKU: {sku})")
            else:
                # Prepare new row
                new_row = [""] * len(headers)
                new_row[name_idx] = name
                new_row[sku_idx] = sku
                new_row[description_idx] = description
                new_row[quote_idx] = quotes_count
                new_row[job_idx] = jobs_count
                new_rows.append(new_row)
                logger.debug(f"Adding new item: {name} (SKU: {sku})")
        
        # Zero out quotes and jobs for rows not in our data - adjust row number
        logger.info("Processing items no longer in inventory data")
        for key, row_idx in existing_rows.items():
            if key not in processed_keys:
                name_val, sku_val = key
                row_num = row_idx + HEADER_ROW_OFFSET - 1  # Adjust for header offset
                cells_to_update.append(gspread.Cell(row=row_num, col=quote_idx+1, value=0))
                cells_to_update.append(gspread.Cell(row=row_num, col=job_idx+1, value=0))
                logger.debug(f"Zeroing out item not in current data: {name_val} (SKU: {sku_val})")
        
        # Add all new rows after the existing data
        if new_rows:
            logger.info(f"Adding {len(new_rows)} new rows to spreadsheet")
            # Get the first empty row after the existing data
            start_row = HEADER_ROW_OFFSET + len(all_values)
            if len(all_values) <= 1:  # Only headers
                start_row = HEADER_ROW_OFFSET + 1
                
            # Use update instead of append_rows to specify exact location
            if new_rows:
                start_cell = f"A{start_row}"
                worksheet.update(start_cell, new_rows, value_input_option='USER_ENTERED')
                logger.debug(f"Added new rows starting at row {start_row}")
        
        # Update existing cells in batches to avoid API limits
        if cells_to_update:
            logger.info(f"Updating {len(cells_to_update)} cells in batches")
            batch_size = 100  # Adjustable based on API limits
            for i in range(0, len(cells_to_update), batch_size):
                batch = cells_to_update[i:i+batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1} with {len(batch)} cells")
                worksheet.update_cells(batch, value_input_option='USER_ENTERED')
                
                # Add a small delay to avoid hitting rate limits
                if i + batch_size < len(cells_to_update):
                    sleep(0.5)
        
        logger.info("Inventory data upload completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading inventory data: {e}", exc_info=True)
        return False

def main():
    """Example usage with the provided sample data"""
    logger.info("Starting main function with sample data")
    sample_data = [
        {
            'description': 'Used for installations over yard or gardens.',
            'jobs_count': 0,
            'name': '1 1/2" x 17.75" x 45.75" Rubber Threshold Ramp',
            'quotes_count': 1,
            'sku': 'RAEZ1310'
        },
        {
            'description': 'Used for installations over yard or gardens.',
            'jobs_count': 0,
            'name': '2" x 23.25" x 46" Rubber Threshold Ramp',
            'quotes_count': 2,
            'sku': 'RAEZ2100'
        },
        {
            'description': 'Patriot Series 3\' long x 36" wide with handrails PS336WR',
            'jobs_count': 1,
            'name': '7/8" x 8" x 41.5" Rubber Threshold Ramp',
            'quotes_count': 0,
            'sku': 'RAEZ0110'
        },
        {
            'description': 'Patriot Series 3\' long x 36" wide with handrails PS336WR',
            'jobs_count': 1,
            'name': 'Big Lug 3\' x 42" wide with 2 line handrail and support',
            'quotes_count': 1,
            'sku': 'BL342WR'
        },
        {
            'description': 'Patriot Series 3\' long x 36" wide with handrails PS336WR',
            'jobs_count': 1,
            'name': 'Big Lug 4\' x 42" wide with 2 line handrail and support',
            'quotes_count': 0,
            'sku': 'BL442WR'
        }
    ]
    
    success = upload_inventory_data(sample_data)
    if success:
        logger.info("Inventory data uploaded successfully!")
    else:
        logger.error("Failed to upload inventory data.")

if __name__ == "__main__":
    main()