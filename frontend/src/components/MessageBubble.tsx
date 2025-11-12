import { Message } from '../types'
import ResourceList from './ResourceList'
import './MessageBubble.css'

interface MessageBubbleProps {
  message: Message
}

const MessageBubble = ({ message }: MessageBubbleProps) => {
  return (
    <div className={`message-bubble ${message.role}`}>
      <div className="message-content">
        {message.content}
      </div>

      {message.role === 'assistant' && (
        <>
          {message.blogs && message.blogs.length > 0 && (
            <ResourceList
              title="Related Blog Articles"
              resources={message.blogs}
              type="blog"
            />
          )}

          {message.repairs && message.repairs.length > 0 && (
            <ResourceList
              title="Repair Guides"
              resources={message.repairs}
              type="repair"
            />
          )}

          {message.parts && message.parts.length > 0 && (
            <ResourceList
              title="Recommended Parts"
              resources={message.parts}
              type="part"
            />
          )}
        </>
      )}
    </div>
  )
}

export default MessageBubble
