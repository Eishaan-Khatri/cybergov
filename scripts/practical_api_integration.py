"""
Practical example: Enhance CyberGov with Polkassembly data
Run with: python scripts/practical_api_integration.py polkadot 1783
"""

import httpx
import json
import sys
from typing import Dict, Any, Optional


class PolkassemblyClient:
    """Client for Polkassembly APIs"""
    
    def __init__(self, network: str):
        self.network = network
        self.base_url = f"https://{network}.polkassembly.io/api"
    
    def get_treasury_stats(self) -> Optional[Dict]:
        """Get current treasury statistics"""
        try:
            response = httpx.get(f"{self.base_url}/v2/meta/treasury-stats", timeout=10.0)
            if response.status_code == 200:
                return response.json()[0]  # Returns array with one item
            return None
        except Exception as e:
            print(f"Error fetching treasury stats: {e}")
            return None
    
    def get_track_counts(self) -> Optional[Dict]:
        """Get active proposal counts per track"""
        try:
            response = httpx.get(f"{self.base_url}/v2/track-counts", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching track counts: {e}")
            return None
    
    def get_delegation_stats(self) -> Optional[Dict]:
        """Get delegation statistics"""
        try:
            response = httpx.get(f"{self.base_url}/v2/delegation/stats", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching delegation stats: {e}")
            return None
    
    def get_proposal_votes(self, proposal_id: int) -> Optional[Dict]:
        """Get votes for a specific proposal"""
        try:
            url = f"{self.base_url}/v2/votes/all?proposalType=referendums_v2&proposalIndex={proposal_id}"
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching votes: {e}")
            return None
    
    def get_bounties_stats(self) -> Optional[Dict]:
        """Get bounties statistics"""
        try:
            response = httpx.get(f"{self.base_url}/v2/bounties/stats", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching bounties stats: {e}")
            return None


def analyze_treasury_health(treasury_stats: Dict) -> Dict[str, Any]:
    """Analyze treasury health for MAGI context"""
    relay_chain = treasury_stats.get("relayChain", {})
    
    # Convert from Planck to DOT (10^10)
    native_token = int(relay_chain.get("nativeToken", 0))
    next_burn = int(relay_chain.get("nextBurn", 0))
    
    dot_balance = native_token / 1e10
    dot_burn = next_burn / 1e10
    
    return {
        "treasury_balance_dot": round(dot_balance, 2),
        "next_burn_dot": round(dot_burn, 2),
        "next_spend_date": relay_chain.get("nextSpendAt"),
        "burn_percentage": round((dot_burn / dot_balance * 100), 2) if dot_balance > 0 else 0,
        "health_status": "healthy" if dot_balance > 10_000_000 else "low"
    }


def analyze_voting_patterns(votes_data: Dict) -> Dict[str, Any]:
    """Analyze voting patterns for a proposal"""
    items = votes_data.get("items", [])
    
    if not items:
        return {"error": "No votes found"}
    
    aye_votes = []
    nay_votes = []
    abstain_votes = []
    
    total_aye_balance = 0
    total_nay_balance = 0
    
    for vote in items:
        decision = vote.get("decision", "").lower()
        balance = vote.get("balance", {})
        
        if balance.get("__typename") == "StandardVoteBalance":
            value = int(balance.get("value", 0))
            
            if decision == "aye":
                aye_votes.append(vote)
                total_aye_balance += value
            elif decision == "nay":
                nay_votes.append(vote)
                total_nay_balance += value
            elif decision == "abstain":
                abstain_votes.append(vote)
    
    total_votes = len(aye_votes) + len(nay_votes) + len(abstain_votes)
    total_balance = total_aye_balance + total_nay_balance
    
    return {
        "total_votes": total_votes,
        "aye_count": len(aye_votes),
        "nay_count": len(nay_votes),
        "abstain_count": len(abstain_votes),
        "aye_percentage": round(len(aye_votes) / total_votes * 100, 2) if total_votes > 0 else 0,
        "aye_balance_dot": round(total_aye_balance / 1e10, 2),
        "nay_balance_dot": round(total_nay_balance / 1e10, 2),
        "aye_balance_percentage": round(total_aye_balance / total_balance * 100, 2) if total_balance > 0 else 0,
        "voting_momentum": "strong_aye" if len(aye_votes) > len(nay_votes) * 2 else 
                          "strong_nay" if len(nay_votes) > len(aye_votes) * 2 else "contested"
    }


def generate_magi_context(
    treasury_health: Dict,
    voting_patterns: Dict,
    delegation_stats: Dict,
    track_counts: Dict
) -> str:
    """Generate enhanced context for MAGI agents"""
    
    context = f"""
<governance_context>

## Treasury Status
- Current Balance: {treasury_health.get('treasury_balance_dot', 'N/A'):,.2f} DOT
- Next Burn: {treasury_health.get('next_burn_dot', 'N/A'):,.2f} DOT ({treasury_health.get('burn_percentage', 0)}%)
- Treasury Health: {treasury_health.get('health_status', 'unknown').upper()}
- Next Spend Period: {treasury_health.get('next_spend_date', 'N/A')}

## Current Voting Patterns
- Total Votes Cast: {voting_patterns.get('total_votes', 0)}
- Aye: {voting_patterns.get('aye_count', 0)} ({voting_patterns.get('aye_percentage', 0)}%)
- Nay: {voting_patterns.get('nay_count', 0)}
- Voting Power (Aye): {voting_patterns.get('aye_balance_dot', 0):,.2f} DOT ({voting_patterns.get('aye_balance_percentage', 0)}%)
- Voting Power (Nay): {voting_patterns.get('nay_balance_dot', 0):,.2f} DOT
- Momentum: {voting_patterns.get('voting_momentum', 'unknown').upper()}

## Delegation Landscape
- Total Delegated: {int(delegation_stats.get('totalDelegatedTokens', 0)) / 1e10:,.2f} DOT
- Active Delegates: {delegation_stats.get('totalDelegates', 0)}
- Total Delegators: {delegation_stats.get('totalDelegators', 0)}

## Track Activity
- Active Proposals: {sum([v for k, v in track_counts.items() if k != 'bounty_dashboard'])}
- Treasury Track: {track_counts.get('Treasurer', 0)} active
- Spender Tracks: {track_counts.get('SmallSpender', 0) + track_counts.get('MediumSpender', 0) + track_counts.get('BigSpender', 0)} active

</governance_context>
"""
    return context


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/practical_api_integration.py <network> <proposal_id>")
        print("Example: python scripts/practical_api_integration.py polkadot 1783")
        sys.exit(1)
    
    network = sys.argv[1]
    proposal_id = int(sys.argv[2])
    
    print(f"\n🔍 Fetching Enhanced Governance Context for {network} Referendum #{proposal_id}\n")
    print("="*80)
    
    # Initialize client
    client = PolkassemblyClient(network)
    
    # Fetch data
    print("\n📊 Fetching data from Polkassembly APIs...")
    treasury_stats = client.get_treasury_stats()
    track_counts = client.get_track_counts()
    delegation_stats = client.get_delegation_stats()
    votes_data = client.get_proposal_votes(proposal_id)
    
    if not all([treasury_stats, track_counts, delegation_stats, votes_data]):
        print("❌ Failed to fetch some data. Check network connectivity.")
        sys.exit(1)
    
    print("✅ All data fetched successfully!\n")
    
    # Analyze data
    print("🧮 Analyzing governance context...")
    treasury_health = analyze_treasury_health(treasury_stats)
    voting_patterns = analyze_voting_patterns(votes_data)
    
    # Generate MAGI context
    magi_context = generate_magi_context(
        treasury_health,
        voting_patterns,
        delegation_stats,
        track_counts
    )
    
    print("\n" + "="*80)
    print("📝 ENHANCED MAGI CONTEXT")
    print("="*80)
    print(magi_context)
    
    # Save to file
    output = {
        "network": network,
        "proposal_id": proposal_id,
        "treasury_health": treasury_health,
        "voting_patterns": voting_patterns,
        "delegation_stats": delegation_stats,
        "track_counts": track_counts,
        "magi_context": magi_context
    }
    
    filename = f"enhanced_context_{network}_{proposal_id}.json"
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Full analysis saved to: {filename}")
    print("\n✅ Done! This context can now be passed to your MAGI agents for better decision-making.\n")


if __name__ == "__main__":
    main()
