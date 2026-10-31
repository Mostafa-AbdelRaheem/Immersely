// src/features/topics/TopicGrid.jsx
import { formatTopic } from '../session/formatTopic'
import './TopicGrid.css'

export default function TopicGrid({ overview, onSelect }) {
  return (
    <div className="topic-grid">
      {overview.map(({ topic, sentence_count, due_count }) => {
        const isEmpty = sentence_count === 0
        return (
          <button
            key={topic}
            type="button"
            className={`topic-card${isEmpty ? ' topic-card--empty' : ''}`}
            onClick={() => onSelect(topic)}
            disabled={isEmpty}
          >
            <span className="topic-card-title">{formatTopic(topic)}</span>
            <span className="topic-card-meta">
              {isEmpty
                ? 'No sentences'
                : `${sentence_count} ${sentence_count === 1 ? 'sentence' : 'sentences'}`}
            </span>
            {!isEmpty && (
              <span className="topic-card-due">
                {due_count > 0 ? `${due_count} due` : 'Nothing due'}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}