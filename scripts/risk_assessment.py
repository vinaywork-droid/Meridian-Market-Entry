"""
risk_assessment.py
------------------
Stage 7: Risk Assessment

Builds a structured risk register for the recommended city (Nagpur).
Each risk is evaluated on likelihood and impact, scored, and assigned
a mitigation strategy.

Output:
  - Risk register CSV
  - Risk heat map (PNG)

Author: Vinay Wakadkar
Project: Meridian Consumer Goods — Market Entry Analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR  = os.path.join(BASE_DIR, 'outputs', 'reports')
os.makedirs(OUT_DIR, exist_ok=True)

def build_risk_register():
    """
    Defines all identified risks for Nagpur market entry.
    Each risk rated on Likelihood (1-5) and Impact (1-5).
    Risk Score = Likelihood × Impact. Max 25.
    """
    risks = [
        {
            'risk_id': 'R01',
            'category': 'Competitive',
            'risk': 'HUL/P&G competitive retaliation',
            'description': 'Incumbent brands respond to Meridian entry with aggressive '
                          'price cuts, increased promotions, or retailer incentives '
                          'to block shelf space.',
            'likelihood': 5,
            'impact': 4,
            'mitigation': 'Secure distribution agreements before public launch. '
                         'Focus on underpenetrated areas where HUL presence is weaker. '
                         'Build retailer loyalty through higher margins in Year 1.',
        },
        {
            'risk_id': 'R02',
            'category': 'Operational',
            'risk': 'Distribution ramp slower than benchmark',
            'description': 'Kirana adoption takes longer than Aurangabad precedent. '
                          'Ramp factor assumptions prove optimistic — breakeven '
                          'pushed beyond Month 14.',
            'likelihood': 4,
            'impact': 4,
            'mitigation': 'Hire experienced local distributor with existing kirana '
                         'relationships. Set Month 3 distribution coverage milestone — '
                         'if below 40%, trigger contingency BTL spend.',
        },
        {
            'risk_id': 'R03',
            'category': 'Financial',
            'risk': 'BTL spend overrun',
            'description': 'Competitive intensity forces higher than budgeted '
                          'marketing spend to achieve trial and visibility. '
                          'Capex ceiling of ₹12 crore breached.',
            'likelihood': 3,
            'impact': 3,
            'mitigation': 'Ring-fence ₹1 crore contingency within capex budget. '
                         'Monthly BTL spend review against distribution milestones. '
                         'Shift spend from ATL to targeted BTL if overrun detected.',
        },
        {
            'risk_id': 'R04',
            'category': 'Operational',
            'risk': 'Logistics cost escalation',
            'description': 'Freight costs increase due to fuel price hikes or '
                          'supply chain disruptions on NH44. '
                          'Current model assumes ₹6,010/MT total cost.',
            'likelihood': 3,
            'impact': 2,
            'mitigation': 'Lock in 12-month freight rate contract with logistics '
                         'partner before entry. Evaluate owned vehicle fleet '
                         'feasibility after Month 12.',
        },
        {
            'risk_id': 'R05',
            'category': 'Market',
            'risk': 'Consumer adoption slower than benchmark',
            'description': 'Nagpur consumers show stronger brand loyalty to HUL '
                          'than Aurangabad benchmark suggests. '
                          'Market share ramp takes 6-9 months longer than projected.',
            'likelihood': 3,
            'impact': 4,
            'mitigation': 'Invest in product sampling campaigns in Month 1-3. '
                         'Price Personal Care SKUs at 5% below HUL for first '
                         '6 months to drive trial. Monitor weekly sell-through rates.',
        },
        {
            'risk_id': 'R06',
            'category': 'Regulatory',
            'risk': 'Trade license or regulatory delays',
            'description': 'Local body approvals, FSSAI compliance, or distributor '
                          'registration delays push launch date by 1-3 months. '
                          'Misses Diwali window.',
            'likelihood': 2,
            'impact': 5,
            'mitigation': 'Begin regulatory process 4 months before planned launch. '
                         'Engage local legal counsel familiar with Nagpur municipal '
                         'requirements. Build 6-week buffer into launch timeline.',
        },
        {
            'risk_id': 'R07',
            'category': 'People',
            'risk': 'Sales team attrition or underperformance',
            'description': 'Field sales representatives leave within first 6 months '
                          'or fail to meet distribution targets. '
                          'Ramp factor directly impacted.',
            'likelihood': 2,
            'impact': 3,
            'mitigation': 'Hire 2 additional reps as buffer beyond the 8 planned. '
                         'Link incentive structure to distribution coverage milestones. '
                         'Monthly performance review with clear targets.',
        },
        {
            'risk_id': 'R08',
            'category': 'Macroeconomic',
            'risk': 'Consumer spending contraction',
            'description': 'Inflation or economic slowdown reduces discretionary '
                          'FMCG spending in SEC B+C households. '
                          'TAM and revenue assumptions overestimated.',
            'likelihood': 2,
            'impact': 3,
            'mitigation': 'Maintain value SKUs (Noodles, Biscuits) at competitive '
                         'price points as defensive play. Monitor RBI inflation '
                         'data quarterly and adjust projections accordingly.',
        },
    ]

    df = pd.DataFrame(risks)
    df['risk_score'] = df['likelihood'] * df['impact']
    df['risk_level'] = df['risk_score'].apply(
        lambda x: 'High' if x >= 15 else ('Medium' if x >= 8 else 'Low')
    )
    df = df.sort_values('risk_score', ascending=False).reset_index(drop=True)

    print("=== RISK REGISTER — NAGPUR MARKET ENTRY ===\n")
    for _, row in df.iterrows():
        print(f"[{row['risk_id']}] {row['risk']} — Score: {row['risk_score']} ({row['risk_level']})")
        print(f"  Likelihood: {row['likelihood']}/5 | Impact: {row['impact']}/5")
        print(f"  Mitigation: {row['mitigation']}\n")

    return df

def plot_risk_heatmap(df):
    """
    Plots risk heat map — likelihood on x-axis, impact on y-axis.
    Each risk plotted as a point. High risk items in top right.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # ── Background zones ───────────────────────────────────────
    # Low risk zone — green
    ax.axhspan(0.5, 2.5, xmin=0, xmax=0.4,  alpha=0.15, color='green')
    ax.axhspan(0.5, 1.5, xmin=0.4, xmax=0.6, alpha=0.15, color='green')

    # High risk zone — red
    ax.axhspan(3.5, 5.5, xmin=0.6, xmax=1.0, alpha=0.15, color='red')
    ax.axhspan(4.5, 5.5, xmin=0.4, xmax=0.6, alpha=0.15, color='red')

    # Medium risk zone — yellow (rest)
    ax.axhspan(0.5, 5.5, xmin=0, xmax=1.0, alpha=0.08, color='yellow')

    # ── Plot each risk ─────────────────────────────────────────
    colors = {'High': '#d62728', 'Medium': '#ff7f0e', 'Low': '#2ca02c'}

    for _, row in df.iterrows():
        color = colors[row['risk_level']]
        ax.scatter(row['likelihood'], row['impact'],
                  s=200, color=color, zorder=5)
        ax.annotate(row['risk_id'],
                   xy=(row['likelihood'], row['impact']),
                   xytext=(8, 8), textcoords='offset points',
                   fontsize=9, fontweight='bold', color=color)

    # ── Labels and formatting ──────────────────────────────────
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xlabel('Likelihood (1=Low, 5=High)', fontsize=12)
    ax.set_ylabel('Impact (1=Low, 5=High)', fontsize=12)
    ax.set_title('Risk Heat Map — Nagpur Market Entry',
                fontsize=14, fontweight='bold')
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.grid(True, alpha=0.3)

    # ── Legend ────────────────────────────────────────────────
    legend_elements = [
        mpatches.Patch(color='#d62728', label='High Risk (Score ≥ 15)'),
        mpatches.Patch(color='#ff7f0e', label='Medium Risk (Score 8-14)'),
        mpatches.Patch(color='#2ca02c', label='Low Risk (Score < 8)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')

    # ── Risk ID reference ──────────────────────────────────────
    reference = '\n'.join([f"{r['risk_id']}: {r['risk']}"
                           for _, r in df.iterrows()])
    fig.text(0.02, 0.02, reference, fontsize=7,
             verticalalignment='bottom', color='grey')

    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'risk_heatmap.png'),
                dpi=150, bbox_inches='tight')
    plt.show()
    print("Risk heat map saved to outputs/reports/risk_heatmap.png")


# ── Main ───────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("MERIDIAN MARKET ENTRY — RISK ASSESSMENT")
    print("=" * 60)

    risk_register = build_risk_register()

    plot_risk_heatmap(risk_register)

    # ── Save risk register ─────────────────────────────────────
    risk_register.to_csv(
        os.path.join(OUT_DIR, 'risk_register.csv'), index=False
    )
    print("\nRisk register saved to outputs/reports/risk_register.csv")
    print("\nRisk assessment complete.")

