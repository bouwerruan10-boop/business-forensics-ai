import ScoreCards from './ScoreCards'
import ImaraScoreHero from './ImaraScoreHero'
import VerdictHero from './VerdictHero'
import AskImara from './AskImara'
import ScoreReasons from './ScoreReasons'
import FinancialRatios from './FinancialRatios'
import FinancialRatioDiagnostics from './FinancialRatioDiagnostics'
import FindingsList from './FindingsList'
import Roadmap from './Roadmap'
import ActionSimulator from './ActionSimulator'
import ActionConstraints from './ActionConstraints'
import EconomicEnvironment from './EconomicEnvironment'
import BankabilityEvidence from './BankabilityEvidence'
import CashFlow13Week from './CashFlow13Week'
import LenderView from './LenderView'
import FundingFit from './FundingFit'
import OwnerRisk from './OwnerRisk'
import FunderGates from './FunderGates'
import InsuranceCession from './InsuranceCession'
import SupplierSavings from './SupplierSavings'
import TaxOptimisation from './TaxOptimisation'
import TaxRiskFlags from './TaxRiskFlags'
import ReportActions from './ReportActions'
import CreditReport from './CreditReport'
import ValuationPanel from './ValuationPanel'
import MarketIntelligence from './MarketIntelligence'
import SACompliancePanel from './SACompliancePanel'
import SectionNav from './SectionNav'
import MethodologyNote from './MethodologyNote'

function Section({ id, title, subtitle, children }) {
  return (
    <section id={id} className="mb-10">
      <div className="mb-4">
        <h2 className="text-white font-bold text-lg">{title}</h2>
        {subtitle && <p className="text-slate-500 text-sm mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

function QuickWins({ findings }) {
  const wins = findings.filter(f => f.quick_win)
  if (!wins.length) return null
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {wins.map((f, i) => (
        <div key={i} className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4">
          <div className="flex items-start gap-2 mb-2">
            <span className="text-emerald-400 text-sm font-bold">⚡</span>
            <span className="text-white text-sm font-medium leading-snug">{f.title}</span>
          </div>
          <p className="text-emerald-400 text-xs font-medium mb-1">{f.financial_impact}</p>
          <p className="text-slate-400 text-xs leading-relaxed">{f.recommendation}</p>
        </div>
      ))}
    </div>
  )
}

function ExecutiveSummaryCard({ report }) {
  const scores = report.scores || {}
  const health = scores.business_health ?? 0
  const color = health >= 70 ? 'text-emerald-400' : health >= 40 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6 sm:p-8">
      <div className="flex flex-col sm:flex-row sm:items-start gap-6">
        {/* Health score ring */}
        <div className="flex-shrink-0 text-center">
          <div className="relative w-24 h-24 mx-auto">
            <svg width="96" height="96" className="-rotate-90">
              <circle cx="48" cy="48" r="40" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
              <circle
                cx="48" cy="48" r="40" fill="none"
                stroke={health >= 70 ? '#22c55e' : health >= 40 ? '#f59e0b' : '#ef4444'}
                strokeWidth="6"
                strokeDasharray={`${2 * Math.PI * 40}`}
                strokeDashoffset={`${2 * Math.PI * 40 * (1 - health / 100)}`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-2xl font-bold ${color}`}>{health}</span>
              <span className="text-slate-600 text-xs">/100</span>
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-2">Health Score</div>
        </div>

        {/* Summary text */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <h3 className="text-white font-bold text-lg">{report.business_name}</h3>
            <span className="text-xs text-slate-500 bg-white/5 border border-white/10 rounded-full px-2 py-0.5">
              {report.industry}
            </span>
            {report.currency && report.annual_revenue > 0 && (
              <span className="text-xs text-slate-500">
                {report.currency} {(report.annual_revenue / 1_000_000).toFixed(1)}M revenue
              </span>
            )}
          </div>
          <div className="flex gap-4 mb-4">
            <div className="text-center">
              <div className="text-red-400 font-bold text-xl">{report.critical_findings}</div>
              <div className="text-slate-600 text-xs">Critical</div>
            </div>
            <div className="text-center">
              <div className="text-orange-400 font-bold text-xl">{report.high_findings}</div>
              <div className="text-slate-600 text-xs">High</div>
            </div>
            <div className="text-center">
              <div className="text-white font-bold text-xl">{report.total_findings}</div>
              <div className="text-slate-600 text-xs">Total</div>
            </div>
          </div>
          {report.situation && (
            <p className="text-slate-400 text-sm leading-relaxed line-clamp-3">{report.situation}</p>
          )}
        </div>
      </div>

      {/* SCR narrative */}
      {(report.complication || report.resolution) && (
        <div className="mt-6 pt-6 border-t border-white/[0.06] grid grid-cols-1 sm:grid-cols-2 gap-4">
          {report.complication && (
            <div>
              <div className="text-xs text-red-400 font-bold uppercase tracking-wide mb-1">Core Problem</div>
              <p className="text-slate-400 text-sm leading-relaxed">{report.complication}</p>
            </div>
          )}
          {report.resolution && (
            <div>
              <div className="text-xs text-emerald-400 font-bold uppercase tracking-wide mb-1">Recommended Action</div>
              <p className="text-slate-400 text-sm leading-relaxed">{report.resolution}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ExecutiveSummaryText({ text }) {
  if (!text) return null
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl p-6 mt-4">
      <div className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-3">Executive Summary</div>
      <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{text}</div>
    </div>
  )
}

export default function Dashboard({ report, analysisId, onNewAnalysis, showToast }) {
  const allFindings = report.all_findings_ranked || []

  // Flatten all findings from department_findings for the filter view
  const allFindingsFlat = (() => {
    const deptFindings = report.department_findings || {}
    const flat = Object.values(deptFindings).flat()
    // Deduplicate by title (the ranked list is top 20; flat has all)
    if (flat.length > allFindings.length) return flat
    return allFindings
  })()

  const navItems = [
    { id: 'summary', label: 'Executive Summary' },
    { id: 'scores', label: 'Health Scores' },
    ...(report.financial_ratios && Object.keys(report.financial_ratios).length > 0 ? [{ id: 'fundamentals', label: 'Financial Fundamentals' }] : []),
    ...(allFindingsFlat.some(f => f.quick_win) ? [{ id: 'quickwins', label: 'Quick Wins' }] : []),
    { id: 'findings', label: 'All Findings' },
    { id: 'roadmap', label: 'Roadmap' },
    ...((report.credit_score > 0 || (report.fraud_risk_level && report.fraud_risk_level !== 'unknown')) ? [{ id: 'credit', label: 'Credit & Fraud' }] : []),
    ...((report.valuation_mid > 0 || report.forecast_base_12m > 0) ? [{ id: 'valuation', label: 'Valuation & Forecast' }] : []),
    ...(report.cashflow_13week?.available ? [{ id: 'cashflow', label: '13-Week Cash Flow' }] : []),
    ...((report.market_search_performed || report.market_visibility_score > 0) ? [{ id: 'market', label: 'Market Intelligence' }] : []),
    ...((report.sa_tax_performed || report.sa_legal_performed) ? [{ id: 'sa-compliance', label: 'SA Compliance' }] : []),
    ...(report.macro_performed ? [{ id: 'economics', label: 'Economic Environment' }] : []),
    ...((report.distress_score?.available || report.bank_signals?.available) ? [{ id: 'evidence', label: 'Bankability Evidence' }] : []),
    ...(report.lender_view?.available ? [{ id: 'lender-view', label: "Lender's-Eye View" }] : []),
    ...(report.funding_fit?.available ? [{ id: 'funding-fit', label: 'Funding Fit' }] : []),
    ...(report.owner_risk?.available ? [{ id: 'owner-risk', label: 'Owner Risk' }] : []),
    ...(report.funder_gates?.available ? [{ id: 'funder-gates', label: 'Funder Gates' }] : []),
    ...(report.insurance_cession?.available ? [{ id: 'insurance-cession', label: 'Insurance & Cession' }] : []),
    ...(report.supplier_benchmark?.available ? [{ id: 'suppliers', label: 'Supplier Savings' }] : []),
    ...(report.tax_optimization?.available ? [{ id: 'tax-optimisation', label: 'Tax Me If You Can' }] : []),
    ...(report.tax_risk_flags?.available ? [{ id: 'tax-risk', label: 'GAAR & SARS Scrutiny' }] : []),
    { id: 'simulator', label: 'Action Simulator' },
    { id: 'methodology', label: 'Methodology' },
  ]

  return (
    <div>
      <ReportActions
        analysisId={analysisId}
        businessName={report.business_name}
        onNewAnalysis={onNewAnalysis}
        showToast={showToast}
      />

      <div className="lg:flex lg:gap-8 lg:items-start">
        <SectionNav items={navItems} />
        <div className="min-w-0 flex-1">

      <VerdictHero report={report} />
      <AskImara report={report} analysisId={analysisId} />

      {/* Executive Summary */}
      <Section id="summary" title="Executive Summary">
        <ExecutiveSummaryCard report={report} />
        {report.executive_summary && (
          <ExecutiveSummaryText text={report.executive_summary} />
        )}
      </Section>

      {/* Score Cards */}
      <Section
        id="scores"
        title="Business Health Scores"
        subtitle="Calculated from findings severity and financial impact across all departments"
      >
        <ImaraScoreHero report={report} />
        <ScoreReasons analysisId={analysisId} />
        <ScoreCards scores={report.scores || {}} report={report} />
      </Section>

      {/* Financial Fundamentals (grounded ratios) */}
      {report.financial_ratios && Object.keys(report.financial_ratios).length > 0 && (
        <Section
          id="fundamentals"
          title="Financial Fundamentals"
          subtitle="Ratios computed directly from your financials — traceable to source figures"
        >
          <FinancialRatios report={report} />
          <FinancialRatioDiagnostics analysisId={analysisId} />
        </Section>
      )}

      {/* Quick Wins */}
      {allFindingsFlat.some(f => f.quick_win) && (
        <Section
          id="quickwins"
          title="⚡ Quick Wins"
          subtitle="Actions implementable in under 30 days with immediate financial return"
        >
          <QuickWins findings={allFindingsFlat} />
        </Section>
      )}

      {/* All Findings */}
      <Section
        id="findings"
        title="All Findings"
        subtitle={`${report.total_findings} findings ranked by severity — click any to expand`}
      >
        <FindingsList findings={allFindingsFlat} />
      </Section>

      {/* Roadmap */}
      <Section
        id="roadmap"
        title="Implementation Roadmap"
        subtitle="90-day action plan derived from findings — Phase 1 actions should begin immediately"
      >
        <Roadmap roadmap={report.implementation_roadmap} />
      </Section>

      {/* Credit Readiness & Fraud Risk */}
      {(report.credit_score > 0 || (report.fraud_risk_level && report.fraud_risk_level !== 'unknown')) && (
        <Section
             id="credit"
          title="Credit Readiness & Fraud Risk"
          subtitle="SA lender creditworthiness assessment and fraud anomaly detection"
        >
          <CreditReport report={report} />
        </Section>
      )}

      {/* Valuation & Forecast */}
      {(report.valuation_mid > 0 || report.forecast_base_12m > 0) && (
        <Section
          id="valuation"
          title="Valuation & Revenue Forecast"
          subtitle="Indicative business valuation range and 12-month scenario forecasts"
        >
          <ValuationPanel report={report} />
        </Section>
      )}

      {/* Market Intelligence */}
      {(report.market_search_performed || report.market_visibility_score > 0) && (
        <Section
          id="market"
          title="Market Intelligence"
          subtitle="Live brand visibility, public sentiment, news coverage, and competitor landscape"
        >
          <MarketIntelligence report={report} />
        </Section>
      )}

      {/* SA Compliance Panel */}
      {(report.sa_tax_performed || report.sa_legal_performed) && (
        <Section
          id="sa-compliance"
          title="SA Compliance Intelligence"
          subtitle="SARS tax obligations, Companies Act, BBBEE, POPIA, and CIPC compliance"
        >
          <SACompliancePanel report={report} />
        </Section>
      )}

      {/* Economic Environment (macro agent + stress test) */}
      {report.macro_performed && (
        <Section
          id="economics"
          title="Economic Environment"
          subtitle="How the SA macro-economy affects this business — and how it holds up under a macro stress test"
        >
          <EconomicEnvironment analysisId={analysisId} currency={report.currency} />
        </Section>
      )}

      {/* Bankability Evidence: Z'' anchor + bank signals + decision-support framing */}
      {(report.distress_score?.available || report.bank_signals?.available) && (
        <Section
          id="evidence"
          title="Bankability Evidence"
          subtitle="Independent distress cross-check, bank-statement cash-flow signals, and how to use this rating"
        >
          <BankabilityEvidence report={report} currency={report.currency} />
        </Section>
      )}

      {/* 13-Week Cash Flow: short-term liquidity horizon */}
      {report.cashflow_13week?.available && (
        <Section
          id="cashflow"
          title="13-Week Cash Flow"
          subtitle="The short-term liquidity horizon — when cash gets tight — complementing the 12-month forecast"
        >
          <CashFlow13Week analysisId={analysisId} currency={report.currency} />
        </Section>
      )}

      {/* Lender's-Eye View: reconciliation, cash-flow conduct, borrowing capacity, decline-risk + Adjusted EBITDA */}
      {report.lender_view?.available && (
        <Section
          id="lender-view"
          title="Lender's-Eye View"
          subtitle="Why a lender would approve or decline you on cash-flow grounds — with the fixes and your true earning power"
        >
          <LenderView analysisId={analysisId} currency={report.currency} />
        </Section>
      )}

      {/* Funding-Fit: which funding archetype fits, with the reasons + fixes */}
      {report.funding_fit?.available && (
        <Section
          id="funding-fit"
          title="Funding Fit"
          subtitle="Which TYPE of funding fits this profile — with what is needed and what to strengthen first"
        >
          <FundingFit analysisId={analysisId} />
        </Section>
      )}

      {/* Owner-level (personal) risk — the blended owner+business exposure SA lenders price in */}
      {report.owner_risk?.available && (
        <Section
          id="owner-risk"
          title="Owner Risk"
          subtitle="The personal exposure a lender sees — surety, key-person dependence, commingling — plus the personal-credit gaps it still needs"
        >
          <OwnerRisk analysisId={analysisId} />
        </Section>
      )}

      {/* Funder gates — named SA funders' published eligibility, you-meet / you-don't */}
      {report.funder_gates?.available && (
        <Section
          id="funder-gates"
          title="Funder Gates"
          subtitle="Which named SA funders (SEDFA, IDC, NEF, Business Partners) your profile fits — gate by gate, with what each still needs"
        >
          <FunderGates analysisId={analysisId} />
        </Section>
      )}

      {/* Insurance + cession — which covers a lender expects ceded as security */}
      {report.insurance_cession?.available && (
        <Section
          id="insurance-cession"
          title="Insurance & Cession"
          subtitle="The cover a lender expects in place and CEDED as security — with the evidence in your documents and the gaps to close"
        >
          <InsuranceCession analysisId={analysisId} />
        </Section>
      )}

      {/* Supplier Savings: expense benchmarking + lower-cost-supplier opportunities */}
      {report.supplier_benchmark?.available && (
        <Section
          id="suppliers"
          title="Supplier Savings"
          subtitle="Per-line-item spend benchmarking and lower-cost suppliers at equivalent service"
        >
          <SupplierSavings report={report} currency={report.currency} />
        </Section>
      )}

      {/* Tax Optimisation: legitimate SA reliefs the SME may be missing (legal planning) */}
      {report.tax_optimization?.available && (
        <Section
          id="tax-optimisation"
          title="Tax Me If You Can"
          subtitle="Legitimate SA tax reliefs you may qualify for but could be missing — legal, GAAR-respecting planning"
        >
          <TaxOptimisation report={report} currency={report.currency} />
        </Section>
      )}

      {/* GAAR / SARS structural tax-risk flags: the mirror of Tax Me If You Can (risk-awareness) */}
      {report.tax_risk_flags?.available && (
        <Section
          id="tax-risk"
          title="GAAR & SARS Scrutiny"
          subtitle="Structural patterns that can attract SARS / GAAR scrutiny — manage with commercial substance and documentation"
        >
          <TaxRiskFlags report={report} />
        </Section>
      )}

      {/* Digital Twin Simulator */}
      <Section
        id="simulator"
        title="Action Simulator"
        subtitle="See the projected outcome of the actions you could take — on your numbers and your Imara Score"
      >
        <ActionSimulator analysisId={analysisId} currency={report.currency} />
        <ActionConstraints analysisId={analysisId} />
      </Section>

      {/* Methodology & confidence */}
      <Section
        id="methodology"
        title="Methodology & Confidence"
        subtitle="How this analysis was produced, how confident it is, and its limits"
      >
        <MethodologyNote report={report} />
      </Section>
        </div>
      </div>
    </div>
  )
}
