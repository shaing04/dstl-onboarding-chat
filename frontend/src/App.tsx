import { useEffect, useState } from 'react';

type Message = {
  id?: number;
  role: string;
  content: string;
  created_at?: string;
  conversation_id?: number;
};

type Conversation = {
  id: number;
  title: string;
  created_at?: string;
  messages: Message[];
};

// Backend API functions
const api = {
  async getConversations(): Promise<Conversation[]> {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/conversations/`,
      );

      if (!response.ok) return [];
      const conversations = await response.json();

      // Fetch messages for each conversation since backend doesn't include them
      const conversationsWithMessages = await Promise.all(
        conversations.map(async (conv: any) => {
          try {
            const messagesResponse = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/conversations/${
                conv.id
              }/messages/`,
            );

            if (messagesResponse.ok) {
              const messages = await messagesResponse.json();
              return { ...conv, messages };
            }
          } catch (error) {
            console.error(
              `Error fetching messages for conversation ${conv.id}:`,
              error,
            );
          }
          return { ...conv, messages: [] };
        }),
      );

      return conversationsWithMessages;
    } catch (error) {
      console.error('Error fetching conversations:', error);
      return [];
    }
  },

  async createConversation(title: string): Promise<Conversation> {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/conversations/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      },
    );
    if (!response.ok) throw new Error('Failed to create conversation');
    return response.json();
  },

  async addMessageToConversation(
    conversationId: number,
    content: string,
    role: 'user' | 'assistant',
  ): Promise<void> {
    await fetch(
      `${
        import.meta.env.VITE_API_BASE_URL
      }/conversations/${conversationId}/messages/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content,
          role,
          conversation_id: conversationId,
        }),
      },
    );
  },

  async getConversationWithMessages(
    conversationId: number,
  ): Promise<Conversation> {
    // Get conversation
    const convResponse = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/conversations/${conversationId}`,
    );
    if (!convResponse.ok) throw new Error('Failed to fetch conversation');
    const conversation = await convResponse.json();

    // Get messages
    const messagesResponse = await fetch(
      `${
        import.meta.env.VITE_API_BASE_URL
      }/conversations/${conversationId}/messages/`,
    );

    const messages = messagesResponse.ok ? await messagesResponse.json() : [];

    return { ...conversation, messages };
  },
};

function App() {
  const [input, setInput] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [isSending, setIsSending] = useState(false);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId,
  );

  // Load conversations on initial render
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await api.getConversations();
        setConversations(data || []);
      } catch (error) {
        console.error('Error loading conversations:', error);
        setConversations([]);
      }
    };
    loadConversations();
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    const userMessage: Message = { role: 'user', content: input };
    setIsSending(true);

    if (activeConversationId === null) {
      try {
        // Create new conversation in backend
        const newConversation = await api.createConversation(
          `Conversation ${Date.now()}`,
        );

        // Add first message to backend
        await api.addMessageToConversation(newConversation.id, input, 'user');

        // Update frontend state
        const newConvWithMessage = {
          ...newConversation,
          messages: [userMessage],
        };
        setConversations((prev) => [...prev, newConvWithMessage]);
        setActiveConversationId(newConversation.id);
      } catch (error) {
        console.error(error);
        alert('Backend error — check server logs');
      }
    } else {
      try {
        // Add message to backend
        await api.addMessageToConversation(activeConversationId, input, 'user');

        // Update frontend state
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConversationId
              ? { ...c, messages: [...c.messages, userMessage] }
              : c,
          ),
        );
      } catch (error) {
        console.error(error);
        alert('Backend error — check server logs');
      }
    }

    setInput('');
    setIsSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isSending) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleConversationClick = async (conversationId: number) => {
    try {
      const fullConversation = await api.getConversationWithMessages(
        conversationId,
      );
      setConversations((prev) =>
        prev.map((c) => (c.id === conversationId ? fullConversation : c)),
      );
      setActiveConversationId(conversationId);
    } catch (error) {
      console.error('Error loading conversation messages:', error);
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white p-4 flex flex-col">
        <div className="mb-4">
          <h1 className="text-xl font-bold">DSTL Chat App</h1>
        </div>
        <button
          className="w-full py-2 px-4 border border-gray-600 rounded hover:bg-gray-800 text-left mb-4"
          onClick={() => setActiveConversationId(null)}
        >
          + New Chat
        </button>
        <div className="flex-1 overflow-y-auto">
          <div className="text-sm text-gray-400">Previous chats...</div>
          <div className="chat-history">
            {conversations &&
              conversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => handleConversationClick(c.id)}
                  className={`cursor-pointer p-2 rounded text-sm ${
                    c.id === activeConversationId
                      ? 'bg-gray-700'
                      : 'hover:bg-gray-800'
                  }`}
                >
                  {c.title}
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeConversation?.messages &&
            activeConversation.messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[70%] rounded-lg p-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white border border-gray-200 text-gray-800'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

          {!activeConversation && (
            <div className="text-center text-gray-500 mt-20">
              <h2 className="text-2xl font-semibold">
                Welcome to the DSTL Chat App
              </h2>
              <p>Select a conversation or start a new one.</p>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-4 max-w-4xl mx-auto">
            <textarea
              className="flex-1 border border-gray-300 rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={1}
              placeholder="Type a message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
            />
            <button
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
              onClick={handleSend}
              disabled={!input.trim() || isSending}
            >
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
          <div className="text-center text-xs text-gray-400 mt-2">
            Press Enter to send
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
