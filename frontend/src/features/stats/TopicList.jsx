// src/features/stats/TopicList.jsx
import { formatPercent, formatTierBreakdown, topicLabel } from './statsFormat'
import './stats.css'

function TopicRow({ stat }) {
  const pct = stat.accuracy === null ? 0 : Math.round(stat.accuracy * 100)
  return (
    <li className={`topic-row${stat.ranked ? '' : ' topic-row--unranked'}`}>
      <div className="topic-row-head">
        <span className="topic-row-name">{topicLabel(stat.topic)}</span>
        <span className="topic-row-pct">{formatPercent(stat.accuracy)}</span>
      </div>
      <div className="topic-row-track" aria-hidden="true">
        <div className="topic-row-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="stats-note">
        {formatTierBreakdown(stat.counts)} · {stat.counts.total}{' '}
        {stat.counts.total === 1 ? 'review' : 'reviews'}
      </span>
    </li>
  )
}

export default function TopicList({ topics }) {
  const ranked = topics.filter((t) => t.ranked)
  const unranked = topics.filter((t) => !t.ranked)

  return (
    <div className="topic-list">
      {ranked.length > 0 && (
        <>
          <h2 className="topic-list-heading">Weakest first</h2>
          <ul className="topic-rows">
            {ranked.map((t) => (
              <TopicRow key={t.topic ?? '__untagged__'} stat={t} />
            ))}
          </ul>
        </>
      )}
      {unranked.length > 0 && (
        <>
          <h2 className="topic-list-heading">Not enough data yet</h2>
          <p className="stats-note">A topic needs 5 reviews to be ranked.</p>
          <ul className="topic-rows">
            {unranked.map((t) => (
              <TopicRow key={t.topic ?? '__untagged__'} stat={t} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}