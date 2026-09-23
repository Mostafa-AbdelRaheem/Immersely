// src/features/session/SceneView.jsx
export default function SceneView({ scene }) {
  const deLines = scene.text_de.split('\n')
  const enLines = scene.text_en.split('\n')
  const targetPositions = new Set(Object.values(scene.line_sentence_map))

  return (
    <div className="scene-card">
      <div className="scene-header">
        <span className="scene-topic">{scene.topic}</span>
        <span className="scene-meta">
          {scene.sentence_ids.length} target
          {scene.sentence_ids.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="scene-lines">
        {deLines.map((line, i) => {
          const isTarget = targetPositions.has(i)
          return (
            <div
              key={i}
              className={`scene-line${isTarget ? ' scene-line--target' : ''}`}
            >
              {isTarget && <span className="scene-line-badge">review</span>}
              <p className="scene-line-de">{line}</p>
              <p className="scene-line-en">{enLines[i]}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}