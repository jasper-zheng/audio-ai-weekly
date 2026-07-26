import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PaperCard from '../components/PaperCard'

const cat = { id: 'foundation', label: '音の基盤モデル', labelEn: 'Audio Foundation Models', labelZh: '音频基础模型', color: '#38bdf8' }
const paper = {
  id: '2601.00001', date: '2026-01-01', title: 'Original English Title', titleJa: '日本語の論文名訳', titleZh: '中文论文标题',
  abstract: 'Original English abstract.', abstractJa: '日本語の要旨。', abstractZh: '中文摘要。',
  what: '日本語の解説。', whatEn: 'English explanation.', whatZh: '中文说明。',
  url: 'https://arxiv.org/abs/2601.00001', nextReads: [],
}

describe('PaperCard localization', () => {
  it('shows the original and translated title in Japanese', () => {
    render(<PaperCard paper={paper} cat={cat} lang="ja" />)
    expect(screen.getByText('Original English Title')).toBeInTheDocument()
    expect(screen.getByText('日本語の論文名訳')).toBeInTheDocument()
    expect(screen.getByText('日本語の解説。')).toBeInTheDocument()
  })

  it('uses English analysis and original abstract in English', () => {
    render(<PaperCard paper={paper} cat={cat} lang="en" />)
    expect(screen.queryByText('日本語の論文名訳')).not.toBeInTheDocument()
    expect(screen.getByText('English explanation.')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Original English Title'))
    expect(screen.getByText('Original English abstract.')).toBeInTheDocument()
    expect(screen.getByText(/Overview \(abstract-based\)/)).toBeInTheDocument()
    expect(screen.getByText('Original abstract')).toBeInTheDocument()
  })

  it('uses Chinese analysis and abstract in Chinese', () => {
    render(<PaperCard paper={paper} cat={cat} lang="zh" />)
    expect(screen.getByText('Original English Title')).toBeInTheDocument()
    expect(screen.getByText('中文论文标题')).toBeInTheDocument()
    expect(screen.queryByText('日本語の論文名訳')).not.toBeInTheDocument()
    expect(screen.getByText('中文说明。')).toBeInTheDocument()
    expect(screen.queryByText('日本語の解説。')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Original English Title'))
    expect(screen.getByText('中文摘要。')).toBeInTheDocument()
    expect(screen.getByText(/概述（基于摘要）/)).toBeInTheDocument()
  })

  it('omits the translated title line when no translation exists', () => {
    const untranslated = { ...paper, titleZh: undefined }
    render(<PaperCard paper={untranslated} cat={cat} lang="zh" />)
    // Falls back to the raw English title, which is already on the first line,
    // so the second line must not repeat it.
    expect(screen.getAllByText('Original English Title')).toHaveLength(1)
  })

  it('shows only sourced affiliations and verified related papers', () => {
    const trustPaper = {
      ...paper,
      org: 'Untrusted legacy value',
      nextReads: [
        { label: 'Legacy candidate', url: 'https://arxiv.org/abs/2401.00001' },
        { label: 'Verified candidate', url: 'https://arxiv.org/abs/2401.00002', verified: true },
      ],
    }
    render(<PaperCard paper={trustPaper} cat={cat} lang="en" />)
    fireEvent.click(screen.getByText('Original English Title'))
    expect(screen.queryByText('Untrusted legacy value')).not.toBeInTheDocument()
    expect(screen.queryByText('Legacy candidate')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Verified candidate' })).toBeInTheDocument()
  })
})
