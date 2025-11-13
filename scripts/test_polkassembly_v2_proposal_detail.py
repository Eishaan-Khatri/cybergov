"""
Test Polkassembly v2 APIs for proposal details and compare with Subsquare
Run with: python scripts/test_polkassembly_v2_proposal_detail.py polkadot 1760
"""

import httpx
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime


class ProposalDataComparison:
    def __init__(self, network: str, proposal_id: int):
        self.network = network
        self.proposal_id = proposal_id
        self.subsquare_base = f"https://{network}-api.subsquare.io"
        self.polkassembly_base = f"https://{network}.polkassembly.io/api"
        
    def fetch_subsquare_proposal(self) -> Optional[Dict]:
        """Fetch proposal from Subsquare API"""
        url = f"{self.subsquare_base}/gov2/referendums/{self.proposal_id}"
        print(f"\n📡 Fetching from Subsquare...")
        print(f"URL: {url}")
        
        try:
            response = httpx.get(url, timeout=15.0)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success - {len(json.dumps(data))} bytes")
                return data
            else:
                print(f"❌ Failed: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def fetch_polkassembly_v2_proposal(self) -> Optional[Dict]:
        """Try different Polkassembly v2 endpoints for proposal details"""
        print(f"\n📡 Fetching from Polkassembly v2...")
        
        # Try multiple v2 endpoints
        endpoints = [
            f"/v2/referenda/{self.proposal_id}",
            f"/v2/posts/on-chain-post?proposalType=referendums_v2&postId={self.proposal_id}",
            f"/v2/listing/on-chain-posts?proposalType=referendums_v2&postId={self.proposal_id}",
        ]
        
        for endpoint in endpoints:
            url = f"{self.polkassembly_base}{endpoint}"
            print(f"\nTrying: {url}")
            
            try:
                response = httpx.get(url, timeout=15.0)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success - {len(json.dumps(data))} bytes")
                    return {"endpoint": endpoint, "data": data}
                else:
                    print(f"❌ Failed: {response.text[:200]}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n⚠️  No v2 endpoint worked for proposal details")
        return None
    
    def fetch_polkassembly_enrichment_data(self) -> Dict[str, Any]:
        """Fetch all available Polkassembly v2 enrichment data"""
        print(f"\n📊 Fetching Polkassembly v2 enrichment data...")
        
        enrichment = {}
        
        # 1. Treasury Stats
        print("\n1️⃣ Treasury Stats...")
        try:
            url = f"{self.polkassembly_base}/v2/meta/treasury-stats"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["treasury_stats"] = response.json()[0]
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Votes for this proposal
        print("\n2️⃣ Proposal Votes...")
        try:
            url = f"{self.polkassembly_base}/v2/votes/all?proposalType=referendums_v2&proposalIndex={self.proposal_id}"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["votes"] = response.json()
                print(f"   ✅ Success - {len(enrichment['votes'].get('items', []))} votes")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Delegation Stats
        print("\n3️⃣ Delegation Stats...")
        try:
            url = f"{self.polkassembly_base}/v2/delegation/stats"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["delegation_stats"] = response.json()
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Track Counts
        print("\n4️⃣ Track Counts...")
        try:
            url = f"{self.polkassembly_base}/v2/track-counts"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["track_counts"] = response.json()
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 5. Bounties Stats
        print("\n5️⃣ Bounties Stats...")
        try:
            url = f"{self.polkassembly_base}/v2/bounties/stats"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["bounties_stats"] = response.json()
                print("   ✅ Success")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 6. Activity Feed (check if proposal appears)
        print("\n6️⃣ Activity Feed...")
        try:
            url = f"{self.polkassembly_base}/v2/activity-feed?page=1&limit=50"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                feed = response.json()
                # Check if our proposal is in the feed
                items = feed.get("items", [])
                our_proposal = next((item for item in items if item.get("index") == self.proposal_id), None)
                if our_proposal:
                    enrichment["activity_feed_entry"] = our_proposal
                    print(f"   ✅ Found proposal in activity feed")
                else:
                    print(f"   ⚠️  Proposal not in recent activity feed")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 7. Tags
        print("\n7️⃣ Available Tags...")
        try:
            url = f"{self.polkassembly_base}/v2/meta/tags"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                enrichment["available_tags"] = response.json()
                print(f"   ✅ Success - {len(enrichment['available_tags'].get('items', []))} tags")
            else:
                print(f"   ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return enrichment
    
    def compare_data_completeness(self, subsquare: Dict, polkassembly_enrichment: Dict):
        """Compare what data each source provides"""
        print(f"\n{'='*80}")
        print("📊 DATA COMPLETENESS COMPARISON")
        print(f"{'='*80}\n")
        
        # Subsquare fields
        subsquare_fields = set(subsquare.keys()) if subsquare else set()
        
        print("🔵 SUBSQUARE DATA FIELDS:")
        print(f"   Total fields: {len(subsquare_fields)}")
        for field in sorted(subsquare_fields):
            value = subsquare.get(field)
            if isinstance(value, (dict, list)):
                print(f"   ✓ {field} ({type(value).__name__})")
            else:
                print(f"   ✓ {field}")
        
        print("\n🟢 POLKASSEMBLY V2 ENRICHMENT DATA:")
        print(f"   Available datasets: {len(polkassembly_enrichment)}")
        for key, value in polkassembly_enrichment.items():
            if value:
                print(f"   ✓ {key}")
            else:
                print(f"   ✗ {key} (failed to fetch)")
    
    def compare_proposal_details(self, subsquare: Dict, polkassembly_enrichment: Dict):
        """Compare specific proposal details"""
        print(f"\n{'='*80}")
        print("📝 PROPOSAL DETAILS COMPARISON")
        print(f"{'='*80}\n")
        
        if not subsquare:
            print("❌ No Subsquare data to compare")
            return
        
        # Basic Info
        print("📌 BASIC INFORMATION:")
        print(f"   Title (Subsquare): {subsquare.get('title', 'N/A')[:80]}")
        
        # Check if we found it in activity feed
        if polkassembly_enrichment.get("activity_feed_entry"):
            pa_title = polkassembly_enrichment["activity_feed_entry"].get("title", "N/A")
            print(f"   Title (Polkassembly): {pa_title[:80]}")
            print(f"   ✅ Titles match: {subsquare.get('title') == pa_title}")
        else:
            print(f"   Title (Polkassembly): Not available in v2 APIs")
        
        print(f"\n   Proposer (Subsquare): {subsquare.get('proposer', 'N/A')}")
        print(f"   Track (Subsquare): {subsquare.get('track', 'N/A')}")
        print(f"   Status (Subsquare): {subsquare.get('state', {}).get('name', 'N/A')}")
        
        # Content
        subsquare_content = subsquare.get('content', '')
        print(f"\n   Content Length (Subsquare): {len(subsquare_content)} chars")
        
        if polkassembly_enrichment.get("activity_feed_entry"):
            pa_content = polkassembly_enrichment["activity_feed_entry"].get("content", "")
            print(f"   Content Length (Polkassembly): {len(pa_content)} chars")
        
        # Spending Info
        print(f"\n💰 SPENDING INFORMATION:")
        if "allSpends" in subsquare and subsquare.get("allSpends"):
            spends = subsquare.get("allSpends", [])
            print(f"   Subsquare allSpends: {len(spends)} items")
            for spend in spends:
                symbol = spend.get("symbol", "?")
                amount = spend.get("amount", 0)
                print(f"      - {amount} {symbol}")
        else:
            print(f"   Subsquare allSpends: Not available or empty")
        
        print(f"   Polkassembly spending: Not available in v2 APIs")
        
        # Tally Info
        print(f"\n🗳️  VOTING TALLY:")
        if "tally" in subsquare:
            tally = subsquare.get("tally", {})
            print(f"   Subsquare tally:")
            print(f"      - Ayes: {tally.get('ayes', 'N/A')}")
            print(f"      - Nays: {tally.get('nays', 'N/A')}")
            print(f"      - Support: {tally.get('support', 'N/A')}")
        
        if polkassembly_enrichment.get("votes"):
            votes = polkassembly_enrichment["votes"].get("items", [])
            aye_count = sum(1 for v in votes if v.get("decision") == "aye")
            nay_count = sum(1 for v in votes if v.get("decision") == "nay")
            print(f"   Polkassembly votes:")
            print(f"      - Aye votes: {aye_count}")
            print(f"      - Nay votes: {nay_count}")
            print(f"      - Total votes: {len(votes)}")
    
    def analyze_polkassembly_enrichment(self, enrichment: Dict):
        """Analyze what unique data Polkassembly provides"""
        print(f"\n{'='*80}")
        print("🌟 POLKASSEMBLY UNIQUE ENRICHMENT DATA")
        print(f"{'='*80}\n")
        
        # Treasury Stats
        if enrichment.get("treasury_stats"):
            treasury = enrichment["treasury_stats"]
            relay_chain = treasury.get("relayChain", {})
            balance = int(relay_chain.get("nativeToken", 0)) / 1e10
            next_burn = int(relay_chain.get("nextBurn", 0)) / 1e10
            
            print("💎 TREASURY HEALTH:")
            print(f"   Current Balance: {balance:,.2f} DOT")
            print(f"   Next Burn: {next_burn:,.2f} DOT ({next_burn/balance*100:.2f}%)")
            print(f"   Next Spend Date: {relay_chain.get('nextSpendAt', 'N/A')}")
            print(f"   Health Status: {'HEALTHY' if balance > 10_000_000 else 'LOW'}")
        
        # Delegation Stats
        if enrichment.get("delegation_stats"):
            delegations = enrichment["delegation_stats"]
            total_delegated = int(delegations.get("totalDelegatedTokens", 0)) / 1e10
            
            print(f"\n🤝 DELEGATION LANDSCAPE:")
            print(f"   Total Delegated: {total_delegated:,.2f} DOT")
            print(f"   Active Delegates: {delegations.get('totalDelegates', 0)}")
            print(f"   Total Delegators: {delegations.get('totalDelegators', 0)}")
            print(f"   Avg per Delegate: {total_delegated/delegations.get('totalDelegates', 1):,.2f} DOT")
        
        # Track Activity
        if enrichment.get("track_counts"):
            tracks = enrichment["track_counts"]
            total_active = sum([v for k, v in tracks.items() if k != 'bounty_dashboard'])
            
            print(f"\n📊 GOVERNANCE ACTIVITY:")
            print(f"   Total Active Proposals: {total_active}")
            print(f"   Treasury Track: {tracks.get('Treasurer', 0)}")
            print(f"   Spender Tracks: {tracks.get('SmallSpender', 0) + tracks.get('MediumSpender', 0) + tracks.get('BigSpender', 0)}")
            print(f"   Root Track: {tracks.get('Root', 0)}")
        
        # Voting Patterns
        if enrichment.get("votes"):
            votes = enrichment["votes"].get("items", [])
            if votes:
                aye_votes = [v for v in votes if v.get("decision") == "aye"]
                nay_votes = [v for v in votes if v.get("decision") == "nay"]
                
                total_aye_balance = sum(int(v.get("balance", {}).get("value", 0)) for v in aye_votes)
                total_nay_balance = sum(int(v.get("balance", {}).get("value", 0)) for v in nay_votes)
                
                print(f"\n🗳️  VOTING MOMENTUM:")
                print(f"   Aye Votes: {len(aye_votes)} ({len(aye_votes)/len(votes)*100:.1f}%)")
                print(f"   Nay Votes: {len(nay_votes)} ({len(nay_votes)/len(votes)*100:.1f}%)")
                print(f"   Aye Voting Power: {total_aye_balance/1e10:,.2f} DOT")
                print(f"   Nay Voting Power: {total_nay_balance/1e10:,.2f} DOT")
                
                if len(aye_votes) > len(nay_votes) * 2:
                    momentum = "STRONG_AYE"
                elif len(nay_votes) > len(aye_votes) * 2:
                    momentum = "STRONG_NAY"
                else:
                    momentum = "CONTESTED"
                print(f"   Momentum: {momentum}")
    
    def generate_recommendation(self, subsquare: Dict, polkassembly_enrichment: Dict):
        """Generate recommendation on which API to use"""
        print(f"\n{'='*80}")
        print("🎯 RECOMMENDATION")
        print(f"{'='*80}\n")
        
        subsquare_score = 0
        polkassembly_score = 0
        
        # Score Subsquare
        if subsquare:
            if subsquare.get("title"):
                subsquare_score += 1
            if subsquare.get("content"):
                subsquare_score += 1
            if subsquare.get("proposer"):
                subsquare_score += 1
            if subsquare.get("allSpends"):
                subsquare_score += 2  # Important for spending analysis
            if subsquare.get("tally"):
                subsquare_score += 1
            if subsquare.get("timeline"):
                subsquare_score += 1
        
        # Score Polkassembly
        if polkassembly_enrichment.get("treasury_stats"):
            polkassembly_score += 2  # Unique and valuable
        if polkassembly_enrichment.get("votes"):
            polkassembly_score += 1
        if polkassembly_enrichment.get("delegation_stats"):
            polkassembly_score += 2  # Unique and valuable
        if polkassembly_enrichment.get("track_counts"):
            polkassembly_score += 1
        if polkassembly_enrichment.get("activity_feed_entry"):
            polkassembly_score += 1
        
        print(f"📊 SCORING:")
        print(f"   Subsquare: {subsquare_score}/7 points")
        print(f"   Polkassembly v2: {polkassembly_score}/7 points")
        
        print(f"\n✅ RECOMMENDATION:")
        print(f"\n   Use BOTH APIs in a dual-source approach:")
        print(f"\n   1. PRIMARY: Subsquare API")
        print(f"      - Proposal title, content, proposer")
        print(f"      - Spending breakdown (allSpends)")
        print(f"      - Vote tally")
        print(f"      - Timeline events")
        print(f"\n   2. ENRICHMENT: Polkassembly v2 APIs")
        print(f"      - Treasury health context")
        print(f"      - Delegation statistics")
        print(f"      - Governance activity metrics")
        print(f"      - Real-time voting patterns")
        
        print(f"\n   ⚠️  IMPORTANT:")
        print(f"      Polkassembly v2 does NOT have a reliable endpoint")
        print(f"      for individual proposal details. Use it ONLY for")
        print(f"      enrichment data (treasury, delegation, votes).")
        
        print(f"\n   💡 IMPLEMENTATION:")
        print(f"      1. Fetch proposal from Subsquare")
        print(f"      2. Fetch enrichment from Polkassembly v2")
        print(f"      3. Merge both in content.md for MAGI agents")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_polkassembly_v2_proposal_detail.py <network> <proposal_id>")
        print("Example: python scripts/test_polkassembly_v2_proposal_detail.py polkadot 1760")
        sys.exit(1)
    
    network = sys.argv[1]
    proposal_id = int(sys.argv[2])
    
    if network not in ["polkadot", "kusama", "paseo"]:
        print(f"Error: Invalid network '{network}'. Must be one of: polkadot, kusama, paseo")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"🔬 TESTING POLKASSEMBLY V2 vs SUBSQUARE")
    print(f"   Network: {network.upper()}")
    print(f"   Proposal: #{proposal_id}")
    print(f"{'='*80}")
    
    comparison = ProposalDataComparison(network, proposal_id)
    
    # Fetch from both sources
    subsquare_data = comparison.fetch_subsquare_proposal()
    polkassembly_proposal = comparison.fetch_polkassembly_v2_proposal()
    polkassembly_enrichment = comparison.fetch_polkassembly_enrichment_data()
    
    # Compare
    comparison.compare_data_completeness(subsquare_data, polkassembly_enrichment)
    comparison.compare_proposal_details(subsquare_data, polkassembly_enrichment)
    comparison.analyze_polkassembly_enrichment(polkassembly_enrichment)
    comparison.generate_recommendation(subsquare_data, polkassembly_enrichment)
    
    # Save results
    results = {
        "network": network,
        "proposal_id": proposal_id,
        "timestamp": datetime.now().isoformat(),
        "subsquare_data": subsquare_data,
        "polkassembly_proposal": polkassembly_proposal,
        "polkassembly_enrichment": polkassembly_enrichment
    }
    
    filename = f"api_comparison_{network}_{proposal_id}_detailed.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"💾 Full results saved to: {filename}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
