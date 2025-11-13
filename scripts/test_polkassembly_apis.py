"""
Test script to explore Polkassembly APIs
Run with: python scripts/test_polkassembly_apis.py
"""

import httpx
import json
from typing import Optional

# Base URLs for different networks
POLKASSEMBLY_BASE_URLS = {
    "polkadot": "https://polkadot.polkassembly.io/api",
    "kusama": "https://kusama.polkassembly.io/api",
    "paseo": "https://paseo.polkassembly.io/api",
}


def test_api_call(url: str, description: str) -> Optional[dict]:
    """Make an API call and print results"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*80}")
    
    try:
        response = httpx.get(url, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Preview:")
            print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None


def main():
    network = "polkadot"  # Change to "kusama" or "paseo" to test other networks
    base_url = POLKASSEMBLY_BASE_URLS[network]
    
    print(f"\n🔍 Testing Polkassembly APIs for {network.upper()}")
    print(f"Base URL: {base_url}")
    
    # Test 1: Get a specific referendum
    proposal_id = 1700  # Recent Polkadot referendum
    test_api_call(
        f"{base_url}/v2/referenda/{proposal_id}",
        f"Get Referendum #{proposal_id} Details"
    )
    
    # Test 2: Get votes for a referendum
    test_api_call(
        f"{base_url}/v2/votes/all?proposalType=referendums_v2&proposalIndex={proposal_id}",
        f"Get Votes for Referendum #{proposal_id}"
    )
    
    # Test 3: Get track analytics
    track_id = 11  # Treasurer track
    test_api_call(
        f"{base_url}/v2/track-analytics/root/{track_id}",
        f"Get Track Analytics for Track #{track_id}"
    )
    
    # Test 4: Get treasury statistics
    test_api_call(
        f"{base_url}/v2/meta/treasury-stats",
        "Get Treasury Statistics"
    )
    
    # Test 5: Get track counts
    test_api_call(
        f"{base_url}/v2/track-counts",
        "Get Track Counts"
    )
    
    # Test 6: Get user by address (CyberGov address)
    cybergov_address = "13Q56KnUmLNe8fomKD3hoY38ZwLKZgRGdY4RTovRNFjMSwKw"
    test_api_call(
        f"{base_url}/v2/users/address/{cybergov_address}",
        f"Get User Profile for CyberGov Address"
    )
    
    # Test 7: Get delegation stats
    test_api_call(
        f"{base_url}/v2/delegation/stats",
        "Get Delegation Statistics"
    )
    
    # Test 8: Get governance analytics - turnout
    test_api_call(
        f"{base_url}/v2/gov-analytics/turnout",
        "Get Governance Turnout Analytics"
    )
    
    # Test 9: Get bounties stats
    test_api_call(
        f"{base_url}/v2/bounties/stats",
        "Get Bounties Statistics"
    )
    
    # Test 10: Get preimages
    test_api_call(
        f"{base_url}/v2/preimages?page=1&limit=5",
        "Get Recent Preimages"
    )
    
    # Test 11: Get activity feed
    test_api_call(
        f"{base_url}/v2/activity-feed?page=1&limit=5",
        "Get Activity Feed"
    )
    
    # Test 12: Get tags
    test_api_call(
        f"{base_url}/v2/meta/tags",
        "Get Available Tags"
    )
    
    print(f"\n{'='*80}")
    print("✅ API Testing Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
