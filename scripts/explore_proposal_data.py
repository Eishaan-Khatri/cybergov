"""
Interactive script to explore proposal data from Polkassembly
Run with: python scripts/explore_proposal_data.py <network> <proposal_id>
Example: python scripts/explore_proposal_data.py polkadot 1100
"""

import httpx
import json
import sys
from typing import Dict, Any


def fetch_polkassembly_proposal(network: str, proposal_id: int) -> Dict[str, Any]:
    """Fetch comprehensive proposal data from Polkassembly"""
    base_url = f"https://{network}.polkassembly.io/api"
    
    print(f"\n🔍 Fetching proposal data for {network} referendum #{proposal_id}")
    print(f"{'='*80}\n")
    
    results = {}
    
    # 1. Get basic proposal info
    print("1️⃣ Fetching basic proposal info...")
    try:
        url = f"{base_url}/v2/referenda/{proposal_id}"
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            results["proposal"] = response.json()
            print(f"   ✅ Title: {results['proposal'].get('title', 'N/A')}")
            print(f"   ✅ Status: {results['proposal'].get('status', 'N/A')}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Get votes
    print("\n2️⃣ Fetching voting data...")
    try:
        url = f"{base_url}/v2/votes/all?proposalType=referendums_v2&proposalIndex={proposal_id}"
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            results["votes"] = response.json()
            votes_data = results["votes"]
            if isinstance(votes_data, dict) and "votes" in votes_data:
                vote_count = len(votes_data["votes"])
                print(f"   ✅ Total votes: {vote_count}")
            else:
                print(f"   ✅ Votes data retrieved")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Get proposer info
    if "proposal" in results and "proposer" in results["proposal"]:
        proposer = results["proposal"]["proposer"]
        print(f"\n3️⃣ Fetching proposer info for {proposer}...")
        try:
            url = f"{base_url}/v2/users/address/{proposer}"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                results["proposer_info"] = response.json()
                print(f"   ✅ Proposer data retrieved")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # 4. Get track info
    if "proposal" in results and "track" in results["proposal"]:
        track_id = results["proposal"]["track"]
        print(f"\n4️⃣ Fetching track analytics for track #{track_id}...")
        try:
            url = f"{base_url}/v2/track-analytics/root/{track_id}"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                results["track_analytics"] = response.json()
                print(f"   ✅ Track analytics retrieved")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # 5. Get comments/timeline
    print(f"\n5️⃣ Fetching proposal timeline...")
    try:
        url = f"{base_url}/v2/referenda/{proposal_id}/timeline"
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            results["timeline"] = response.json()
            print(f"   ✅ Timeline retrieved")
        else:
            print(f"   ⚠️  Timeline endpoint may not exist: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    return results


def save_results(results: Dict[str, Any], network: str, proposal_id: int):
    """Save results to a JSON file"""
    filename = f"polkassembly_{network}_{proposal_id}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {filename}")


def print_summary(results: Dict[str, Any]):
    """Print a summary of the fetched data"""
    print(f"\n{'='*80}")
    print("📊 DATA SUMMARY")
    print(f"{'='*80}\n")
    
    if "proposal" in results:
        proposal = results["proposal"]
        print(f"Title: {proposal.get('title', 'N/A')}")
        print(f"Proposer: {proposal.get('proposer', 'N/A')}")
        print(f"Track: {proposal.get('track', 'N/A')}")
        print(f"Status: {proposal.get('status', 'N/A')}")
        
        if "requested" in proposal:
            print(f"Requested Amount: {proposal.get('requested', 'N/A')}")
    
    if "votes" in results:
        print(f"\nVoting Data: Available")
    
    if "proposer_info" in results:
        print(f"Proposer Info: Available")
    
    if "track_analytics" in results:
        print(f"Track Analytics: Available")
    
    print(f"\n{'='*80}\n")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/explore_proposal_data.py <network> <proposal_id>")
        print("Example: python scripts/explore_proposal_data.py polkadot 1100")
        sys.exit(1)
    
    network = sys.argv[1]
    proposal_id = int(sys.argv[2])
    
    if network not in ["polkadot", "kusama", "paseo"]:
        print(f"Error: Invalid network '{network}'. Must be one of: polkadot, kusama, paseo")
        sys.exit(1)
    
    # Fetch data
    results = fetch_polkassembly_proposal(network, proposal_id)
    
    # Print summary
    print_summary(results)
    
    # Save to file
    save_results(results, network, proposal_id)
    
    print("✅ Done! Check the JSON file for full details.")


if __name__ == "__main__":
    main()
