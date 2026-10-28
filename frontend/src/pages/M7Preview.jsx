// src/pages/M7Preview.jsx  — TEMPORARY, delete after checking
import { useState } from 'react'
import ChunkView from '../features/session/ChunkView'
import GradeChips from '../features/session/GradeChips'
import SessionSummary from '../features/session/SessionSummary'
import CorrectionFeedback from '../features/session/CorrectionFeedback'

const noop = () => {}
const sceneChunk = {
  filler_lines: ['Kellner: Guten Abend! Was darf es sein?'],
  target: { sentence_id: 'A', speaker: 'Gast', hint_en: 'I would like a coffee.' },
}
const isoChunk = {
  filler_lines: [],
  target: { sentence_id: 'B', speaker: null, hint_en: 'I reserved a table for two.' },
}
const closing = { filler_lines: ['Kellner: Perfekt, folgen Sie mir.'], target: null }
const summary = {
  total: 3, tiers: { correct: 1, almost_correct: 1, incorrect: 1 },
  grades: { again: 1, hard: 0, good: 2, easy: 0 }, overrides: 1,
  nextDue: '2026-10-27T20:00:00Z',
}

export default function M7Preview() {
  const [grade, setGrade] = useState('hard')
  const h = (t) => <h3 style={{ margin: '1.5rem 0 0.5rem' }}>{t}</h3>
  return (
    <div>
      {h('1. Scene, hint hidden')}
      <ChunkView chunk={sceneChunk} mode="scene" phase="answering" hintVisible={false} onRevealHint={noop} onSubmit={noop} />
      {h('2. Scene, hint shown')}
      <ChunkView chunk={sceneChunk} mode="scene" phase="answering" hintVisible onSubmit={noop} />
      {h('3. Checking (locked)')}
      <ChunkView chunk={sceneChunk} mode="scene" phase="checking" hintVisible onSubmit={noop} />
      {h('4. Failed check (error)')}
      <ChunkView chunk={sceneChunk} mode="scene" phase="answering" hintVisible={false} error="Too many requests. Please wait a moment and try again." onRevealHint={noop} onSubmit={noop} />
      {h('5. Isolated (English is the cue)')}
      <ChunkView chunk={isoChunk} mode="isolated" phase="answering" hintVisible onSubmit={noop} />
      {h('6. Feedback + grade chips (click to override)')}
      <CorrectionFeedback result={{ tier: 'almost_correct', corrected_input: 'Ich liebe dich', diff_note: 'du → dich (accusative)', rule_practiced: null }} />
      <GradeChips selected={grade} suggested="hard" onSelect={setGrade} />
      {h('7. Chips disabled (saving)')}
      <GradeChips selected="good" suggested="good" disabled onSelect={noop} />
      {h('8. Closing chunk')}
      <ChunkView chunk={closing} mode="scene" phase="closing" onFinish={noop} />
      {h('9. Summary')}
      <SessionSummary summary={summary} onRestart={noop} />
    </div>
  )
}