import { useState, useEffect } from 'react';
import { Bot } from 'lucide-react';
import { AIChat } from '../components/chat/AIChat';
import { sendAssistantMessage, getProjects } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';
import { RiskBadge } from '../components/ui/RiskBadge';
import { RiskScore } from '../components/ui/RiskScore';

const suggestedQuestions: string[] = [
  "Which projects are at highest risk?",
  "Why is the River Basin Development Project high risk?",
  "Which sector has the highest average cost overrun?",
  "Show me projects likely to be delayed.",
  "What are the major risk drivers?",
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);

  useEffect(() => {
    getProjects()
      .then(setProjects)
      .catch(() => setProjects([]))
      .finally(() => setProjectsLoading(false));
  }, []);

  const handleSend = async (content: string) => {
    if (isTyping) return;
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const result = await sendAssistantMessage(content);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.reply,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I couldn't process that request. Please try again.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsTyping(false);
    }
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

      <div className="mb-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-navy-900">Monitored Projects</h2>
        </div>
        {projectsLoading ? (
          <LoadingState text="Loading projects..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3 font-semibold lg:px-6">Project</th>
                  <th className="px-4 py-3 font-semibold">Risk Level</th>
                  <th className="px-4 py-3 font-semibold">Risk Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {projects.map((project: any) => (
                  <tr key={project.id} className="transition-colors hover:bg-blue-50/40">
                    <td className="max-w-[320px] px-4 py-3 lg:px-6">
                      <div className="truncate font-medium text-navy-900" title={project.name}>
                        {project.name}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={project.riskLevel} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <RiskScore score={project.riskScore} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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