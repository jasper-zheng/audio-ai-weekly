import { localized, t } from '../i18n.js'

export default function FeatureSpotlight({ feature, lang = 'ja' }) {
  if (!feature?.slug) return null

  const copy = t(lang)
  const title = localized(feature, 'title', lang)
  const dek = localized(feature, 'dek', lang)
  const type = copy.featureTypes[feature.type] || feature.type
  const readTime = localized(feature, 'readTimeMinutes', lang)
  // Japanese is the default edition and lives at the article root.
  const languageDir = lang === 'ja' ? '' : `${lang}/`
  const articleHref = `./features/${encodeURIComponent(feature.slug)}/${languageDir}`
  const archiveHref = `./features/${languageDir}`

  return (
    <section className="feature-spotlight fd" aria-labelledby={`feature-${feature.slug}`}>
      <div className="feature-spotlight-heading">
        <div style={{ fontSize: 11, color: '#f472b6', letterSpacing: 3, fontWeight: 600 }}>
          {copy.latestFeature}
        </div>
        <a href={archiveHref} className="feature-archive-link">
          {copy.featureArchive} <span aria-hidden="true">→</span>
        </a>
      </div>

      <div className="feature-meta">
        <span>{type}</span>
        <span aria-hidden="true">/</span>
        <time dateTime={feature.date}>{feature.date}</time>
        <span aria-hidden="true">/</span>
        <span>{copy.readTime(readTime)}</span>
        <span aria-hidden="true">/</span>
        <span>{copy.sourceCount(feature.sourceCount)}</span>
        <span aria-hidden="true">/</span>
        <span>{copy.featureDisclosure}</span>
      </div>

      <h2 id={`feature-${feature.slug}`} className="feature-title">
        <a href={articleHref}>{title}</a>
      </h2>
      {dek && <p className="feature-dek">{dek}</p>}
      <a href={articleHref} className="feature-read-link"
        aria-label={`${copy.readFeature}: ${title}`}>
        {copy.readFeature} <span aria-hidden="true">→</span>
      </a>
    </section>
  )
}
