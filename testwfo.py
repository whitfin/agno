import requests

# Configuration
endpoint = "https://inventory.dearsystems.com/ExternalApi/v2/product?page=2&limit=1"
account_id = "api-auth-accountid: 3e58b3ae-00b9-4632-826c-b4e9b9745321"  # Replace with your account ID
application_key = "api-auth-applicationkey: 3e6b4852-a792-629f-c3dd-2cb4a056ed88"  # Replace with your application key

# Set up headers
headers = {
    "Content-type": "application/json",
    "api-auth-accountid": "3e58b3ae-00b9-4632-826c-b4e9b9745321",
    "api-auth-applicationkey": "3e6b4852-a792-629f-c3dd-2cb4a056ed88"
}

# Make GET request with custom headers
response = requests.get(endpoint, headers=headers)

# Handle response
if response.status_code == 200:
    print("Success!")
    print(f"Response status code: {response.status_code}")
    print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
    print("Response content:")
    print(response.text)  # Print raw response text instead of trying to parse JSON
else:
    print(f"Failed with status code {response.status_code}")
    print(response.text)