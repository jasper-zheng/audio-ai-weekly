import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TrendSummary from '../components/TrendSummary'

describe('TrendSummary', () => {
  it('renders all trend lines', () => {
    const trend = ['音響基盤モデルの研究が進んだ', '音声生成の品質が向上した', 'ニューラル音声コーデックが注目を集めた']
    render(<TrendSummary trend={trend} />)
    expect(screen.getByText(/音響基盤モデルの研究が進んだ/)).toBeInTheDocument()
    expect(screen.getByText(/音声生成の品質が向上した/)).toBeInTheDocument()
    expect(screen.getByText(/ニューラル音声コーデックが注目を集めた/)).toBeInTheDocument()
  })

  it('renders the Chinese heading and lines when lang is zh', () => {
    const trend = ['音频生成的质量有所提升', '神经音频编解码器受到关注']
    render(<TrendSummary trend={trend} lang="zh" />)
    expect(screen.getByText(/本周技术趋势/)).toBeInTheDocument()
    expect(screen.getByText(/音频生成的质量有所提升/)).toBeInTheDocument()
  })

  it('strips circled number prefixes from trend lines', () => {
    const trend = ['① 音響基盤モデルの研究', '② 音声生成の進展']
    render(<TrendSummary trend={trend} />)
    expect(screen.getByText(/音響基盤モデルの研究/)).toBeInTheDocument()
    expect(screen.queryByText(/①/)).not.toBeInTheDocument()
  })

  it('renders number prefixes 1. 2. 3.', () => {
    const trend = ['A', 'B', 'C']
    render(<TrendSummary trend={trend} />)
    expect(screen.getByText('1.')).toBeInTheDocument()
    expect(screen.getByText('2.')).toBeInTheDocument()
    expect(screen.getByText('3.')).toBeInTheDocument()
  })

  it('renders empty trend gracefully', () => {
    const { container } = render(<TrendSummary trend={[]} />)
    expect(container.querySelectorAll('div > div').length).toBeGreaterThan(0)
  })

  it('renders section header', () => {
    render(<TrendSummary trend={[]} />)
    expect(screen.getByText(/今週の技術トレンド/)).toBeInTheDocument()
  })
})
