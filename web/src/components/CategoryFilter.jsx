import { FIELD_SUFFIX, localized, t } from '../i18n.js'
export default function CategoryFilter({ categories, active, onChange, lang = 'ja' }) {
  // The synthetic "all" tab is already localized, so give every language the
  // same value rather than relying on which suffix localized() reaches for.
  const allLabels = Object.fromEntries(
    Object.values(FIELD_SUFFIX).map(suffix => [`label${suffix}`, t(lang).all]),
  )
  const all = [{ id: 'all', ...allLabels, color: '#64748b', papers: [] }, ...categories]
  return (
    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
      {all.map(cat => (
        <button key={cat.id} className="catBtn"
          style={active === cat.id ? { borderColor: cat.color, color: cat.color, background: `${cat.color}10` } : {}}
          onClick={() => onChange(cat.id)}>
          {localized(cat, 'label', lang)}
        </button>
      ))}
    </div>
  )
}
