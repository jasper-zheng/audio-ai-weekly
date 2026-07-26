import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CategoryFilter from '../components/CategoryFilter'

const CATS = [
  { id: 'foundation', label: '音の基盤モデル', labelEn: 'Audio Foundation Models', labelZh: '音频基础模型', color: '#38bdf8', papers: [] },
  { id: 'generation', label: '音声生成',       labelEn: 'Audio Generation',        labelZh: '音频生成',     color: '#4ade80', papers: [] },
  { id: 'codec',      label: '音声コーデック',  labelEn: 'Audio Codec',             labelZh: '音频编解码',   color: '#fb923c', papers: [] },
]

describe('CategoryFilter', () => {
  it('renders すべて button', () => {
    render(<CategoryFilter categories={CATS} active="all" onChange={() => {}} />)
    expect(screen.getByText('すべて')).toBeInTheDocument()
  })

  it('renders all category buttons', () => {
    render(<CategoryFilter categories={CATS} active="all" onChange={() => {}} />)
    expect(screen.getByText('音の基盤モデル')).toBeInTheDocument()
    expect(screen.getByText('音声生成')).toBeInTheDocument()
    expect(screen.getByText('音声コーデック')).toBeInTheDocument()
  })

  it('renders English labels when lang is en', () => {
    render(<CategoryFilter categories={CATS} active="all" onChange={() => {}} lang="en" />)
    expect(screen.getByText('All')).toBeInTheDocument()
    expect(screen.getByText('Audio Foundation Models')).toBeInTheDocument()
    expect(screen.getByText('Audio Codec')).toBeInTheDocument()
    expect(screen.queryByText('音声生成')).not.toBeInTheDocument()
  })

  it('renders Chinese labels when lang is zh', () => {
    render(<CategoryFilter categories={CATS} active="all" onChange={() => {}} lang="zh" />)
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('音频基础模型')).toBeInTheDocument()
    expect(screen.getByText('音频生成')).toBeInTheDocument()
    expect(screen.getByText('音频编解码')).toBeInTheDocument()
    expect(screen.queryByText('音声生成')).not.toBeInTheDocument()
  })

  it('falls back to English then Japanese when a Chinese label is missing', () => {
    const partial = [{ id: 'legacy', label: '旧カテゴリ', labelEn: 'Legacy', color: '#888', papers: [] }]
    render(<CategoryFilter categories={partial} active="all" onChange={() => {}} lang="zh" />)
    expect(screen.getByText('Legacy')).toBeInTheDocument()
  })

  it('calls onChange with correct id when clicked', () => {
    const onChange = vi.fn()
    render(<CategoryFilter categories={CATS} active="all" onChange={onChange} />)
    fireEvent.click(screen.getByText('音声生成'))
    expect(onChange).toHaveBeenCalledWith('generation')
  })

  it('calls onChange with all when すべて clicked', () => {
    const onChange = vi.fn()
    render(<CategoryFilter categories={CATS} active="foundation" onChange={onChange} />)
    fireEvent.click(screen.getByText('すべて'))
    expect(onChange).toHaveBeenCalledWith('all')
  })

  it('renders nothing for empty categories', () => {
    const { container } = render(<CategoryFilter categories={[]} active="all" onChange={() => {}} />)
    expect(container.querySelectorAll('button')).toHaveLength(1) // Only the "All" button.
  })
})
