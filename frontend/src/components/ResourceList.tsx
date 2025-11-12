import { Blog, Repair, Part } from '../types'
import './ResourceList.css'

interface ResourceListProps {
  title: string
  resources: (Blog | Repair | Part)[]
  type: 'blog' | 'repair' | 'part'
}

const ResourceList = ({ title, resources, type }: ResourceListProps) => {
  const getTypeEmoji = () => {
    switch (type) {
      case 'blog':
        return '📝'
      case 'repair':
        return '🔧'
      case 'part':
        return '⚙️'
      default:
        return '📄'
    }
  }

  return (
    <div className="resource-list">
      <h4 className="resource-title">
        {getTypeEmoji()} {title}
      </h4>
      <ul className="resource-items">
        {resources.map((resource, index) => (
          <li key={index} className="resource-item">
            <a
              href={resource.url}
              target="_blank"
              rel="noopener noreferrer"
              className="resource-link"
            >
              <span className="resource-name">{resource.name}</span>
              <span className="resource-score">
                {(resource.similarity_score * 100).toFixed(0)}% match
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ResourceList
