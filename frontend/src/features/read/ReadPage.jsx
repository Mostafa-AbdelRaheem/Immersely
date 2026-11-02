// src/features/read/ReadPage.jsx
import { useCallback, useEffect, useState } from 'react'
import { createArticle, deleteArticle, listArticles } from '../../api/articles'
import { formatTopic } from '../session/formatTopic'
import TopicGrid from '../topics/TopicGrid'
import { useTopicOverview } from '../topics/useTopicOverview'
import ArticleView from './ArticleView'
import './ReadPage.css'

export default function ReadPage() {
  const { overview, isLoading, error: overviewError } = useTopicOverview()
  const [topic, setTopic] = useState(null)
  const [articles, setArticles] = useState([])
  const [openId, setOpenId] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(async (t) => {
    try {
      setArticles(await listArticles(t))
    } catch {
      setError('Could not load your articles. Please try again.')
    }
  }, [])

  useEffect(() => {
    if (topic) load(topic)
  }, [topic, load])

  function handleSelect(t) {
    setError(null)
    setOpenId(null)
    setArticles([])
    setTopic(t)
  }

  async function handleGenerate() {
    if (isGenerating) return
    setIsGenerating(true)
    setError(null)
    try {
      const created = await createArticle(topic)
      setArticles((prev) => [created, ...prev])
      setOpenId(created.id)
    } catch (err) {
      setError(
        err.status === 404
          ? 'You have no sentences in this topic yet.'
          : 'Could not generate an article right now. Please try again.',
      )
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleDelete(id) {
    setDeletingId(id)
    setError(null)
    try {
      await deleteArticle(id)
      setArticles((prev) => prev.filter((a) => a.id !== id))
      setOpenId((cur) => (cur === id ? null : cur))
    } catch {
      setError('Could not delete the article. Please try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const opened = articles.find((a) => a.id === openId)

  return (
    <div className="read-page">
      <h1 className="page-title">Read</h1>
      <p className="page-subtitle">Pick a topic to read or generate an article from your sentences.</p>

      {isLoading && <p className="page-subtitle">Loading your topics…</p>}
      {overviewError && <p className="form-error">{overviewError}</p>}
      {!isLoading && <TopicGrid overview={overview} onSelect={handleSelect} />}

      {topic && (
        <section className="read-articles">
          <div className="read-articles-header">
            <h2>{formatTopic(topic)}</h2>
            <button
              type="button"
              className="btn btn-primary"
              disabled={isGenerating}
              onClick={handleGenerate}
            >
              {isGenerating ? 'Generating…' : 'Generate new article'}
            </button>
          </div>

          {error && <p className="form-error">{error}</p>}
          {articles.length === 0 && !error && (
            <p className="page-subtitle">No articles yet for this topic.</p>
          )}

          <ul className="read-list">
            {articles.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  className={`read-list-item${a.id === openId ? ' read-list-item--open' : ''}`}
                  onClick={() => setOpenId(a.id === openId ? null : a.id)}
                >
                  <span>{a.title}</span>
                  <span className="read-list-date">
                    {new Date(a.generated_at).toLocaleDateString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {opened && (
            <ArticleView
              article={opened}
              isDeleting={deletingId === opened.id}
              onDelete={() => handleDelete(opened.id)}
            />
          )}
        </section>
      )}
    </div>
  )
}