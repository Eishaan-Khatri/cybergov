"""
Test working Polkassembly APIs with correct parameters
Run with: python scripts/test_working_apis.py
"""

import httpx
import json


def test_api(url: str, description: str):
    """Test an API endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print(f"{'='*80}")
    
    try:
        response = httpx.get(url, timeout=15.0)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS")
            print(json.dumps(data, indent=2)[:800])
            if len(json.dumps(data)) > 800:
                print("... (truncated)")
            return data
        else:
            print(f"❌ FAILED: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def main():
    network = "polkadot"
    base = f"https://{network}.polkassembly.io/api"
    
    print(f"\n🔍 Testing Working Polkassembly APIs for {network.upper()}\n")
    
    # 1. Treasury Stats - WORKS
    test_api(
        f"{base}/v2/meta/treasury-stats",
        "Treasury Statistics"
    )
    
    # 2. Track Counts - WORKS
    test_api(
        f"{base}/v2/track-counts",
        "Track Counts (Active Proposals per Track)"
    )
    
    # 3. Delegation Stats - WORKS
    test_api(
        f"{base}/v2/delegation/stats",
        "Delegation Statistics"
    )
    
    # 4. Bounties Stats - WORKS
    test_api(
        f"{base}/v2/bounties/stats",
        "Bounties Statistics"
    )
    
    # 5. Preimages - WORKS
    test_api(
        f"{base}/v2/preimages?page=1&limit=3",
        "Recent Preimages"
    )
    
    # 6. Activity Feed - WORKS
    test_api(
        f"{base}/v2/activity-feed?page=1&limit=3",
        "Activity Feed (Recent Proposals)"
    )
    
    # 7. Tags - WORKS
    test_api(
        f"{base}/v2/meta/tags",
        "Available Tags"
    )
    
    # 8. Votes for a specific proposal - WORKS
    proposal_id = 1783  # Recent active proposal
    test_api(
        f"{base}/v2/votes/all?proposalType=referendums_v2&proposalIndex={proposal_id}",
        f"Votes for Referendum #{proposal_id}"
    )
    
    # 9. Get specific referendum using correct endpoint
    # Note: The v2/referenda endpoint seems to need specific proposal type
    test_api(
        f"{base}/v1/posts/on-chain-post?proposalType=referendums_v2&postId={proposal_id}",
        f"Referendum #{proposal_id} Details (v1 endpoint)"
    )
    
    # 10. List referendums
    test_api(
        f"{base}/v1/listing/on-chain-posts?proposalType=referendums_v2&page=1&listingLimit=3",
        "List Recent Referendums (v1 endpoint)"
    )
    
    print(f"\n{'='*80}")
    print("✅ Testing Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
