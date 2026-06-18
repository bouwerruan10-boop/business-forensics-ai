function SentimentBadge({ sentiment }) {
  const map = {
    positive: { label: 'Positive', cls: 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' },
    neutral:  { label: 'Neutral',  cls: 'bg-amber-400/10 text-amber-400 border-amber-400/20' },
    negative: { label: 'Negative', cls: 'bg-red-400/10 text-red-400 border-red-400/20' },
    unknown:  { label: 'Unknown',  cls: 'bg-slate-400/10 text-slate-400 border-slate-400/20' },
  }
  const { label, cls } = map[sentiment] || map.unknown
  return (
    <span className={`text-xs border rounded-full px-2.5 py-1 font-semibold ${cls}`}>
      {label}
    </span>
  )
}

function VisibilityBar({ score }) {
  const color = score >= 70 ? 'bg-emerald-400' : score >= 40 ? 'bg-amber-400' : 'bg-red-400'
  const label = score >= 70 ? 'Good' : score >= 40 ? 'Needs Work' : score > 0 ? 'Low' : 'Not Found'
  const textColor = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-red-400'
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-slate-400 text-xs">Market Visibility</span>
        <span className={`text-sm font-bold ${textColor}`}>{score}/100 · {label}</span>
      </div>
      <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ${color}`}
          style={{ width: `${Math.max(score, 2)}%` }}
        />
      </div>
    </div>
  )
}

function NewsCard({ article, i }) {
  return (
    <a
      href={article.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] rounded-xl p-3.5 transition-colors"
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-white text-xs font-medium leading-snug line-clamp-2">
          {article.title || 'Untitled article'}
        </span>
        <span className="flex-shrink-0 text-slate-600 text-[10px]">↗</span>
      </div>
      <div className="flex items-center gap-2">
        {article.source && (
          <span className="text-slate-500 text-[11px]">{article.source}</span>
        )}
        {article.date && (
          <span className="text-slate-600 text-[11px]">{article.date}</span>
        )}
      </div>
      {article.snippet && (
        <p className="text-slate-400 text-[11px] leading-relaxed mt-1.5 line-clamp-2">
          {article.snippet}
        </p>
      )}
    </a>
  )
}

function CompetitorChip({ name }) {
  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-lg px-3 py-1.5 text-slate-300 text-xs">
      {name}
    </div>
  )
}

function ListSection({ title, items, icon, emptyText, accentClass }) {
  if (!items || !items.length) return null
  return (
    <div>
      <h4 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
        {icon} {title}
      </h4>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className={`flex items-start gap-2 text-xs leading-relaxed ${accentClass || 'text-slate-300'}`}>
            <span className="mt-0.5 flex-shrink-0">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function MarketIntelligence({ report }) {
  const score       = report.market_visibility_score ?? 0
  const sentiment   = report.market_sentiment || 'unknown'
  const news        = report.market_news || []
  const competitors = report.market_competitors || []
  const opps        = report.market_opportunities || []
  const risks       = report.market_risks || []
  const searched    = report.market_search_performed
  const totalHits   = report.market_total_results || 0

  // Don't render the panel if the agent hasn't run at all
  if (!searched && !score) return null

  const noPresence = searched && totalHits === 0

  return (
    <div className="bg-navy-card border border-white/[0.08] rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
        <div>
          <h3 className="text-white font-semibold text-sm">Market Intelligence</h3>
          <p className="text-slate-500 text-xs mt-0.5">
            {searched
              ? `Live search · ${totalHits} results found across news, web & social`
              : 'Industry context · live search not configured'}
          </p>
        </div>
        <SentimentBadge sentiment={sentiment} />
      </div>

      <div className="p-6 space-y-6">

        {/* Visibility bar */}
        <VisibilityBar score={score} />

        {/* No presence warning */}
        {noPresence && (
          <div className="bg-red-400/5 border border-red-400/20 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <span className="text-red-400 text-lg flex-shrink-0">⚠</span>
              <div>
                <p className="text-red-400 text-sm font-semibold mb-1">No online presence detected</p>
                <p className="text-slate-400 text-xs leading-relaxed">
                  A Google search for <span className="text-white font-medium">"{report.business_name}"</span> returned
                  no results. This is a significant trust and discoverability barrier — customers, partners,
                  and lenders searching for this business online will find nothing.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* No API key notice */}
        {!searched && (
          <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
            <p className="text-amber-400 text-xs font-semibold mb-1">Live search not configured</p>
            <p className="text-slate-400 text-xs leading-relaxed">
              Add a <span className="text-white font-mono text-[11px]">SERPER_API_KEY</span> to your Railway
              environment variables to enable live Google search, news, and social media analysis for each report.
              Free tier at serper.dev — 2,500 searches/month.
            </p>
          </div>
        )}

        {/* News coverage */}
        {news.length > 0 && (
          <div>
            <h4 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-3">
              📰 News & Media Coverage
            </h4>
            <div className="space-y-2">
              {news.slice(0, 5).map((article, i) => (
                <NewsCard key={i} article={article} i={i} />
              ))}
            </div>
          </div>
        )}

        {news.length === 0 && searched && (
          <div>
            <h4 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
              📰 News & Media Coverage
            </h4>
            <p className="text-slate-500 text-xs italic">
              No news articles found for this company. Consider publishing press releases or thought leadership content to build media presence.
            </p>
          </div>
        )}

        {/* Competitors */}
        {competitors.length > 0 && (
          <div>
            <h4 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-3">
              🏢 Competitors Identified
            </h4>
            <div className="flex flex-wrap gap-2">
              {competitors.map((c, i) => (
                <CompetitorChip key={i} name={c} />
              ))}
            </div>
          </div>
        )}

        {/* Opportunities & Risks side-by-side on wide, stacked on mobile */}
        {(opps.length > 0 || risks.length > 0) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {opps.length > 0 && (
              <ListSection
                title="Market Opportunities"
                items={opps}
                icon="🚀"
                accentClass="text-emerald-400"
              />
            )}
            {risks.length > 0 && (
              <ListSection
                title="Market Risks"
                items={risks}
                icon="⚠️"
                accentClass="text-amber-400"
              />
            )}
          </div>
        )}

      </div>
    </div>
  )
}
