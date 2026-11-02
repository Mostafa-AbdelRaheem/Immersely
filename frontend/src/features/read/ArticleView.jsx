// src/features/read/ArticleView.jsx
import { useState } from 'react'
import './ArticleView.css'

// Splits on blank lines so each paragraph becomes its own <p>.
function toParagraphs(text) {
  return text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean)
}

export default function ArticleView({ article, onDelete, isDeleting }) {
  const [showEnglish, setShowEnglish] = useState(false)

  return (
    <article className="article-view">
      <h2 className="article-title">{article.title}</h2>

      <div className="article-body" lang="de">
        {toParagraphs(article.text_de).map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      {showEnglish && (
        <div className="article-english" lang="en">
          {toParagraphs(article.text_en).map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      )}

      <div className="article-actions">
        <button
          type="button"
          className="btn"
          aria-pressed={showEnglish}
          onClick={() => setShowEnglish((v) => !v)}
        >
          {showEnglish ? 'Hide English' : 'Show English'}
        </button>
        <button
          type="button"
          className="btn article-delete"
          disabled={isDeleting}
          onClick={onDelete}
        >
          {isDeleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </article>
  )
}