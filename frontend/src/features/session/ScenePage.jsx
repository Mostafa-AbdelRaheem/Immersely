// src/features/session/ScenePage.jsx
import { useState } from 'react'
import { requestScene } from '../../api/scenes'
import { useTopics } from '../../context/TopicsContext'
import SceneView from './SceneView'

export default function ScenePage() {
  const { topics, isLoading: topicsLoading } = useTopics()
  const [selectedTopic, setSelectedTopic] = useState('')
  const [scene, setScene] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [noDue, setNoDue] = useState(false)

  async function handleGetScene() {
    if (!selectedTopic) return

    setIsLoading(true)
    setError(null)
    setNoDue(false)
    setScene(null)

    try {
      const data = await requestScene(selectedTopic)
      setScene(data)
    } catch (err) {
      if (err.status === 404) {
        setNoDue(true)
      } else {
        setError('Could not generate a scene right now. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="scene-page">
      <h1>Review a scene</h1>
      <p className="home-subtitle">Pick a topic to see a generated review scene.</p>

      <div className="filter-bar">
        <label htmlFor="scene-topic">Topic:</label>
        <select
          id="scene-topic"
          value={selectedTopic}
          onChange={(e) => setSelectedTopic(e.target.value)}
          disabled={topicsLoading}
        >
          <option value="">Select a topic…</option>
          {topics.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          className="btn btn-primary"
          onClick={handleGetScene}
          disabled={!selectedTopic || isLoading}
        >
          {isLoading ? 'Generating…' : 'Get scene'}
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      {noDue && (
        <p className="empty-state">
          Nothing due for "{selectedTopic}" right now — check back later.
        </p>
      )}

      {scene && <SceneView scene={scene} />}
    </div>
  )
}