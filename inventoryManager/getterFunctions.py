import requests
import pprint
from queryCost import extract_query_cost, log_query_cost
from config import API_VERSION

fetch_jobs_all_data_query = """
    query FetchComprehensiveJobsData($after: String, $limit: Int!) {
      jobs(first: $limit, after: $after) {
        nodes {
          id
          arrivalWindow {
            startAt
            endAt
          }
          billingType
          bookingConfirmationSentAt
          client {
            id
            firstName
            lastName
          }
          customFields {
            __typename
            ... on CustomFieldText {
              id
              valueText
            }
          }
          defaultVisitTitle
          expenses(first: 10) {
            nodes {
              id
              description
              createdAt
            }
          }
          instructions
          # Removed invoiceSchedule field that was causing errors
          jobberWebUri
          jobCosting {
            totalRevenue
            totalCost
            profitAmount
          }
          jobNumber
          jobStatus
          jobType
          lineItems(first: 50) {
            nodes {
              id
              name
              description
              quantity
              unitCost
              totalPrice
              totalCost
              category
              taxable
              createdAt
              updatedAt
              linkedProductOrService {
                id
                name
                description
                category
                defaultUnitCost
                internalUnitCost
                markup
                taxable
                visible
              }
            }
          }
          noteAttachments(first: 10) {
            nodes {
              id
              fileName
              fileSize
              createdAt
              updatedAt
            }
          }
          paymentRecords(first: 10) {
            nodes {
              id
              amount
            }
          }
          property {
            id
            street
            city
            province
            postalCode
            country
          }
          quote {
            id
            quoteNumber
            createdAt
          }
          source
          title
          total
          visits(first: 10) {
            nodes {
              id
              title
              completedAt
            }
          }
          # Removed visitsInfo field that was causing errors
          # Removed visitSchedule field that was causing errors
          willClientBeAutomaticallyCharged
          completedAt
          createdAt
          endAt
          startAt
          updatedAt
        }
        pageInfo {
          endCursor
          hasNextPage
        }
      }
    }
    """

fetch_jobs_query = """
query FetchJobLineItems($after: String, $limit: Int!) {
  jobs(first: $limit, after: $after) {
    nodes {
      id
      jobNumber
      title
      lineItems(first: 10) {
        nodes {
          id
          name
          description
          quantity
          unitCost
          totalPrice
          totalCost
          category
          taxable
          createdAt
          updatedAt
          linkedProductOrService {
            id
            name
            description
            category
            defaultUnitCost
            internalUnitCost
            markup
            taxable
            visible
          }
        }
      }
    }
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
"""

def fetch_quotes(access_token, limit=5):
    """Fetch a limited number of quotes from the Jobber GraphQL API"""
    graphql_url = "https://api.getjobber.com/api/graphql"
    
    # GraphQL query to fetch quotes with basic information
    query = """
    query FetchQuotes {
      quotes(first: %d) {
        nodes {
          id
          title
          quoteNumber
          quoteStatus
          amounts {
            subtotal
            total
          }
          client {
            firstName
            lastName
          }
          createdAt
        }
      }
    }
    """ % limit
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": API_VERSION
    }
    
    response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": query}
    )
    
    if response.status_code == 200:
        response_data = response.json()
        # Log query cost information
        log_query_cost(response_data, "Fetch Quotes")
        return response_data
    else:
        raise Exception(f"Failed to fetch quotes: {response.text}")

def fetch_jobs(access_token, after=None, limit=5):
    """Fetch a limited number of jobs with all available fields from the Jobber GraphQL API"""
    graphql_url = "https://api.getjobber.com/api/graphql"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": API_VERSION
    }
    
    # Create variables object with both cursor and limit
    variables = {
        "limit": limit
    }
    if after:
        variables["after"] = after
    
    response = requests.post(
        graphql_url,
        headers=headers,
        json={
            "query": fetch_jobs_query,
            "variables": variables
        }
    )
    
    if response.status_code == 200:
        response_data = response.json()
        # Log query cost information
        log_query_cost(response_data, "Fetch Jobs")
        return response_data
    else:
        raise Exception(f"Failed to fetch jobs: {response.text}")

def fetch_jobs_all_data(access_token, after=None, limit=8):
    graphql_url = "https://api.getjobber.com/api/graphql"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": API_VERSION
    }
    
    # Create variables object with both cursor and limit
    variables = {
        "limit": limit
    }
    if after:
        variables["after"] = after
    
    response = requests.post(
        graphql_url,
        headers=headers,
        json={
            "query": fetch_jobs_all_data_query,
            "variables": variables
        }
    )
    
    if response.status_code == 200:
        response_data = response.json()
        # Log query cost information
        log_query_cost(response_data, "Fetch Jobs")
        return response_data
    else:
        raise Exception(f"Failed to fetch jobs: {response.text}")

def get_job_count(access_token):
    """Get the total count of jobs from the Jobber GraphQL API"""
    graphql_url = "https://api.getjobber.com/api/graphql"
    
    # GraphQL query to get only the total count of jobs
    query = """
    query GetJobCount {
      jobs {
        totalCount
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": API_VERSION
    }
    
    response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": query}
    )
    
    if response.status_code == 200:
        response_data = response.json()
        # Log query cost information
        log_query_cost(response_data, "Get Job Count")
        
        # Extract and return the count
        return response_data.get('data', {}).get('jobs', {}).get('totalCount', 0)
    else:
        raise Exception(f"Failed to get job count: {response.text}")

def get_quote_count(access_token):
    """Get the total count of quotes from the Jobber GraphQL API"""
    graphql_url = "https://api.getjobber.com/api/graphql"
    
    # GraphQL query to get only the total count of quotes
    query = """
    query GetQuoteCount {
      quotes {
        totalCount
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-JOBBER-GRAPHQL-VERSION": API_VERSION
    }
    
    response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": query}
    )
    
    if response.status_code == 200:
        response_data = response.json()
        # Log query cost information
        log_query_cost(response_data, "Get Quote Count")
        
        # Extract and return the count
        return response_data.get('data', {}).get('quotes', {}).get('totalCount', 0)
    else:
        raise Exception(f"Failed to get quote count: {response.text}")

