import { useState } from 'react';
import { Bot } from 'lucide-react';
import { AIChat } from '../components/chat/AIChat';
import { suggestedQuestions, mockResponses } from '../data/chat';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

function findResponse(input: string): string {
  const lower = input.toLowerCase();
  for (const [key, value] of Object.entries(mockResponses)) {
    if (key !== 'default' && lower.includes(key)) {
      return value;
    }
  }
  return mockResponses['default'];
}

// Replace mock assistant logic with LLM API later.
// The findResponse lookup above will be swapped for:
//   POST /api/assistant/query  ->  { reply }
export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = (content: string) => {
    if (isTyping) return;
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: findResponse(content),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsTyping(false);
    }, 700);
  };

  return (
    <div className="mx-auto min-w-0 max-w-[1000px]">
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-blue-50 p-2.5 ring-1 ring-inset ring-blue-100">
            <Bot className="h-7 w-7 text-blue-600" />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-navy-900 lg:text-3xl">GovRisk AI</h1>
            <p className="text-sm font-medium text-gray-600">Infrastructure Intelligence Assistant</p>
          </div>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Ask questions about projects, risks, delays and portfolio performance.
        </p>
      </div>

      <div className="flex h-[calc(100vh-13rem)] min-h-[440px] flex-col overflow-hidden rounded-xl border border-gray-200 bg-white">
        <AIChat
          messages={messages}
          onSend={handleSend}
          suggestedQuestions={messages.length === 0 ? suggestedQuestions : undefined}
          isTyping={isTyping}
        />
      </div>
    </div>
  );
}
