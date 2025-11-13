"""
Compare data from Subsquare vs Polkassembly APIs
Run with: python scripts/compare_api_sources.py <network> <proposal_id>
Example: python scripts/compare_api_sources.py polkadot 1100
"""

import httpx
import json
import sys
from typing import Dict, Any


def fetch_subsquare_data(network: str, proposal_id: int) -> Dict[str, Any]:
    """Fetch data from Subsquare API (current source)"""
    base_url = f"https://{network}-api.subsquare.io/gov2/referendums"
    url = f"{base_url}/{proposal_id}"
    
    print(f"📡 Fetching from Subsquare: {url}")
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ❌ Subsquare failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"   ❌ Subsquare error: {e}")
        return {}


def fetch_polkassembly_data(network: str, proposal_id: int) -> Dict[str, Any]:
    """Fetch data from Polkassembly API"""
    base_url = f"https://{network}.polkassembly.io/api"
    url = f"{base_url}/v2/referenda/{proposal_id}"
    
    print(f"📡 Fetching from Polkassembly: {url}")
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"   ❌ Polkassembly failed: {response.status_code}")
            return {}
    except Exception as e:
        print(f"   ❌ Polkassembly error: {e}")
        return {}


def compare_fields(subsquare: Dict, polkassembly: Dict):
    """Compare available fields between the two sources"""
    print(f"\n{'='*80}")
    print("📊 FIELD COMPARISON")
    print(f"{'='*80}\n")
    
    subsquare_keys = set(subsquare.keys())
    polkassembly_keys = set(polkassembly.keys())
    
    common_keys = subsquare_keys & polkassembly_keys
    subsquare_only = subsquare_keys - polkassembly_keys
    polkassembly_only = polkassembly_keys - subsquare_keys
    
    print(f"✅ Common fields ({len(common_keys)}):")
    for key in sorted(common_keys):
        print(f"   - {key}")
    
    print(f"\n🔵 Subsquare only ({len(subsquare_only)}):")
    for key in sorted(subsquare_only):
        print(f"   - {key}")
    
    print(f"\n🟢 Polkassembly only ({len(polkassembly_only)}):")
    for key in sorted(polkassembly_only):
        print(f"   - {key}")


def compare_content(subsquare: Dict, polkassembly: Dict):
    """Compare specific content fields"""
    print(f"\n{'='*80}")
    print("📝 CONTENT COMPARISON")
    print(f"{'='*80}\n")
    
    # Title
    print("Title:")
    print(f"  Subsquare:    {subsquare.get('title', 'N/A')[:80]}")
    print(f"  Polkassembly: {polkassembly.get('title', 'N/A')[:80]}")
    
    # Content length
    subsquare_content = subsquare.get('content', '')
    polkassembly_content = polkassembly.get('content', '')
    print(f"\nContent Length:")
    print(f"  Subsquare:    {len(subsquare_content)} chars")
    print(f"  Polkassembly: {len(polkassembly_content)} chars")
    
    # Proposer
    print(f"\nProposer:")
    print(f"  Subsquare:    {subsquare.get('proposer', 'N/A')}")
    print(f"  Polkassembly: {polkassembly.get('proposer', 'N/A')}")
    
    # Track
    print(f"\nTrack:")
    print(f"  Subsquare:    {subsquare.get('track', 'N/A')}")
    print(f"  Polkassembly: {polkassembly.get('track', 'N/A')}")
    
    # Status
    print(f"\nStatus:")
    print(f"  Subsquare:    {subsquare.get('state', {}).get('name', 'N/A')}")
    print(f"  Polkassembly: {polkassembly.get('status', 'N/A')}")


def analyze_unique_features(subsquare: Dict, polkassembly: Dict):
    """Analyze unique features from each source"""
    print(f"\n{'='*80}")
    print("🔍 UNIQUE FEATURES ANALYSIS")
    print(f"{'='*80}\n")
    
    print("Subsquare Unique Features:")
    if "tally" in subsquare:
        print(f"  ✅ Tally data: {subsquare['tally']}")
    if "timeline" in subsquare:
        print(f"  ✅ Timeline: {len(subsquare.get('timeline', []))} events")
    if "allSpends" in subsquare:
        print(f"  ✅ Spending breakdown: {len(subsquare.get('allSpends', []))} items")
    
    print("\nPolkassembly Unique Features:")
    if "comments" in polkassembly:
        print(f"  ✅ Comments: Available")
    if "reactions" in polkassembly:
        print(f"  ✅ Reactions: Available")
    if "tags" in polkassembly:
        print(f"  ✅ Tags: {polkassembly.get('tags', [])}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_api_sources.py <network> <proposal_id>")
        print("Example: python scripts/compare_api_sources.py polkadot 1100")
        sys.exit(1)
    
    network = sys.argv[1]
    proposal_id = int(sys.argv[2])
    
    if network not in ["polkadot", "kusama", "paseo"]:
        print(f"Error: Invalid network '{network}'. Must be one of: polkadot, kusama, paseo")
        sys.exit(1)
    
    print(f"\n🔬 Comparing API sources for {network} referendum #{proposal_id}\n")
    
    # Fetch from both sources
    subsquare_data = fetch_subsquare_data(network, proposal_id)
    polkassembly_data = fetch_polkassembly_data(network, proposal_id)
    
    if not subsquare_data and not polkassembly_data:
        print("\n❌ Failed to fetch data from both sources!")
        sys.exit(1)
    
    # Compare
    if subsquare_data and polkassembly_data:
        compare_fields(subsquare_data, polkassembly_data)
        compare_content(subsquare_data, polkassembly_data)
        analyze_unique_features(subsquare_data, polkassembly_data)
    
    # Save comparison
    comparison = {
        "subsquare": subsquare_data,
        "polkassembly": polkassembly_data
    }
    
    filename = f"api_comparison_{network}_{proposal_id}.json"
    with open(filename, "w") as f:
        json.dump(comparison, f, indent=2)
    
    print(f"\n💾 Full comparison saved to: {filename}")
    print("\n✅ Comparison complete!")


if __name__ == "__main__":
    main()
