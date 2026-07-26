export const DEFAULT_LANGUAGE = 'en'
export const SUPPORTED_LANGUAGES = ['ja', 'en', 'zh']
export const LANGUAGE_STORAGE_KEY = 'arxiv-language'

/**
 * Field-name suffix for AI-written prose. Japanese is the unsuffixed base field
 * because it was the original output language.
 */
export const FIELD_SUFFIX = { ja: '', en: 'En', zh: 'Zh' }

/**
 * Suffix for fields whose base value is the raw English arXiv text
 * (`title`, `abstract`), where Japanese is the suffixed variant instead.
 */
export const SOURCE_FIELD_SUFFIX = { ja: 'Ja', en: '', zh: 'Zh' }

/** Fallback order when a language is missing a field. */
export const FALLBACK_ORDER = { ja: ['en'], en: ['ja'], zh: ['en', 'ja'] }

/**
 * BCP-47 tags for the document language. Chinese needs the script subtag: the
 * page fonts ship no CJK glyphs, so the browser resolves Han characters via the
 * document language, and a bare "zh" renders Japanese glyph variants.
 */
export const HTML_LANG = { ja: 'ja', en: 'en', zh: 'zh-Hans' }

/** Browser-language prefixes, longest first so zh-Hant still resolves to zh. */
const BROWSER_PREFIXES = [['ja', 'ja'], ['zh', 'zh'], ['en', 'en']]

const messages = {
  ja: {
    siteTitle: '音響AI週報',
    subtitle: '音の基盤モデル・音声生成・音声コーデック',
    showingPapers: n => `${n} 論文 表示中`,
    period: '期間:', allPeriod: '全期間', count: n => `${n}件`, all: 'すべて',
    search: 'キーワード検索...', citations: '引用数順', date: '日付順',
    favorites: 'お気に入り', papers: n => `${n} 論文`,
    trendTitle: '◈ 今週の技術トレンド（3行まとめ）',
    loading: '読み込み中...', loadingOlder: '過去の週を読み込み中...', allLoaded: '- 全期間を読み込みました -',
    footer: '音響AI週報 - arXiv cs.SD / eess.AS - AIによる分類・翻訳を含みます - 毎週金曜更新',
    read: '既読', unread: '未読', markRead: '既読にする', markUnread: '未読に戻す',
    addFavorite: 'お気に入りに追加', removeFavorite: 'お気に入り解除', scrollTop: 'トップへ戻る',
    abstract: 'AIによる抄録和訳（未校閲）', cited: n => `引用 ${n}`, week: '週',
    latestFeature: 'LATEST FEATURE / 最新特集', featureArchive: '特集アーカイブ',
    featureTypes: { primer: '分野を解く', debate: '論点を読む' },
    readTime: n => `読了 ${n}分`, sourceCount: n => `出典 ${n}件`, readFeature: '特集を読む',
    weeklyDisclosure: 'AI生成（タイトル・抄録ベース）・人手未校閲',
    weeklyCaution: '誤訳、誤要約、過度な一般化を含む可能性があります。研究上の判断は原論文で確認してください。',
    featureDisclosure: 'AI生成（タイトル・抄録ベース）・出典と翻訳の機械的整合性チェック済み・人手未校閲',
    arxivAcknowledgement: 'Thank you to arXiv for use of its open access interoperability. This service was not reviewed or approved by, nor does it necessarily express or reflect the policies or opinions of, arXiv.',
    arxivAcknowledgementLabel: 'arXiv公式英文（原文）',
    primaryNavigation: 'メインナビゲーション',
    sections: ['概要（抄録ベース）', '著者が主張する新規性・差分（抄録ベース）', '抄録で説明される技術・手法', '抄録に記載された検証', '抄録から読み取れる注意点（推定を含む）', '検証済みの関連論文候補'],
    pageTitle: '音響AI週報',
  },
  en: {
    siteTitle: 'Audio AI Weekly',
    subtitle: 'Audio foundation models, audio generation, and neural audio codecs',
    showingPapers: n => `Showing ${n} papers`,
    period: 'Period:', allPeriod: 'All time', count: n => `${n} papers`, all: 'All',
    search: 'Search keywords...', citations: 'Most cited', date: 'Newest',
    favorites: 'Favorites', papers: n => `${n} papers`,
    trendTitle: "◈ This week's technical trends (3 highlights)",
    loading: 'Loading...', loadingOlder: 'Loading older weeks...', allLoaded: '- all weeks loaded -',
    footer: 'Audio AI Weekly - arXiv cs.SD / eess.AS - Includes AI-assisted classification and translation - UPDATED FRIDAYS',
    read: 'Read', unread: 'Unread', markRead: 'Mark as read', markUnread: 'Mark as unread',
    addFavorite: 'Add to favorites', removeFavorite: 'Remove from favorites', scrollTop: 'Back to top',
    abstract: 'Original abstract', cited: n => `cited ${n}`, week: 'WEEK',
    latestFeature: 'LATEST FEATURE', featureArchive: 'Feature archive',
    featureTypes: { primer: 'Field Primer', debate: 'Debate Brief' },
    readTime: n => `${n} min read`, sourceCount: n => `${n} sources`, readFeature: 'Read feature',
    weeklyDisclosure: 'AI-generated from titles and abstracts · not human-reviewed',
    weeklyCaution: 'May contain mistranslations, inaccurate summaries, or overgeneralizations; consult the original paper for research decisions.',
    featureDisclosure: 'AI-generated from titles and abstracts · machine-checked for source and translation consistency · not human-reviewed',
    arxivAcknowledgement: 'Thank you to arXiv for use of its open access interoperability. This service was not reviewed or approved by, nor does it necessarily express or reflect the policies or opinions of, arXiv.',
    arxivAcknowledgementLabel: 'Official arXiv statement',
    primaryNavigation: 'Primary navigation',
    sections: ['Overview (abstract-based)', 'Author-claimed novelty and differences (abstract-based)', 'Method described in the abstract', 'Validation reported in the abstract', 'Cautions inferred from the abstract', 'Verified related-paper candidates'],
    pageTitle: 'Audio AI Weekly',
  },
  zh: {
    siteTitle: '音频AI周报',
    subtitle: '音频基础模型・音频生成・音频编解码',
    showingPapers: n => `正在显示 ${n} 篇论文`,
    period: '时间范围:', allPeriod: '全部时间', count: n => `${n} 篇`, all: '全部',
    search: '关键词搜索...', citations: '按引用数', date: '按日期',
    favorites: '收藏', papers: n => `${n} 篇论文`,
    trendTitle: '◈ 本周技术趋势（三点速览）',
    loading: '加载中...', loadingOlder: '正在加载往期...', allLoaded: '- 已加载全部时间 -',
    footer: '音频AI周报 - arXiv cs.SD / eess.AS - 含 AI 分类与翻译 - 每周五更新',
    read: '已读', unread: '未读', markRead: '标记为已读', markUnread: '标记为未读',
    addFavorite: '加入收藏', removeFavorite: '取消收藏', scrollTop: '返回顶部',
    abstract: 'AI 摘要中译（未校阅）', cited: n => `引用 ${n}`, week: '周',
    latestFeature: 'LATEST FEATURE / 最新专题', featureArchive: '专题列表',
    featureTypes: { primer: '领域解读', debate: '论点透视' },
    readTime: n => `阅读 ${n} 分钟`, sourceCount: n => `来源 ${n} 篇`, readFeature: '阅读专题',
    weeklyDisclosure: 'AI 生成（基于标题与摘要）· 未经人工校阅',
    weeklyCaution: '可能包含误译、错误摘要或过度概括；研究决策请以原论文为准。',
    featureDisclosure: 'AI 生成（基于标题与摘要）· 已完成来源与翻译的机械一致性检查 · 未经人工校阅',
    arxivAcknowledgement: 'Thank you to arXiv for use of its open access interoperability. This service was not reviewed or approved by, nor does it necessarily express or reflect the policies or opinions of, arXiv.',
    arxivAcknowledgementLabel: 'arXiv 官方英文声明（原文）',
    primaryNavigation: '主导航',
    sections: ['概述（基于摘要）', '作者主张的新颖性与差异（基于摘要）', '摘要中描述的方法', '摘要中报告的验证', '从摘要推断的注意事项（含推测）', '已核实的相关论文候选'],
    pageTitle: '音频AI周报',
  },
}

export function isLanguage(value) { return SUPPORTED_LANGUAGES.includes(value) }
export function browserLanguage(languages = globalThis.navigator?.languages ?? [globalThis.navigator?.language]) {
  const preferred = languages.filter(Boolean)[0]?.toLowerCase() ?? ''
  return BROWSER_PREFIXES.find(([prefix]) => preferred.startsWith(prefix))?.[1] ?? DEFAULT_LANGUAGE
}
export function resolveLanguage(queryValue, storedValue, languages) {
  if (isLanguage(queryValue)) return queryValue
  if (isLanguage(storedValue)) return storedValue
  return browserLanguage(languages)
}
export function t(lang) { return messages[isLanguage(lang) ? lang : DEFAULT_LANGUAGE] }

/** Walk `lang` then its fallbacks over a suffix table, returning the first value. */
function pick(record, key, lang, suffixes) {
  if (!record) return ''
  const order = [isLanguage(lang) ? lang : DEFAULT_LANGUAGE, ...(FALLBACK_ORDER[lang] ?? [])]
  for (const code of order) {
    const value = record[`${key}${suffixes[code]}`]
    if (value) return value
  }
  return ''
}

/** Read an AI-written field (`what` / `whatEn` / `whatZh`). */
export function localized(record, key, lang) {
  return pick(record, key, lang, FIELD_SUFFIX)
}

/** Read a field whose base value is raw arXiv English (`title` / `titleJa` / `titleZh`). */
export function localizedSource(record, key, lang) {
  return pick(record, key, lang, SOURCE_FIELD_SUFFIX)
}

/** Every per-language variant of a field, for building a language-blind search index. */
export function allVariants(record, key, suffixes = FIELD_SUFFIX) {
  return SUPPORTED_LANGUAGES.map(code => record?.[`${key}${suffixes[code]}`] ?? '')
}
