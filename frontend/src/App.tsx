import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import Modal from './components/Modal';
import './App.css';

interface DocumentSnippet {
  id: string;
  title: string;
  similarity: number;
  content: string;
  metadata?: Record<string, unknown>;
}

interface VectorStoreConfig {
  name: string;
  chunkSize: number;
  overlap: number;
  topK: number;
}

interface VectorStoreResponse {
  id: string;
  name: string;
  status: string;
  documentTaskId: string;
  config: VectorStoreConfig;
  createdAt: string;
  updatedAt: string;
  failureReason?: string | null;
}

interface CreateVectorStoreResponse {
  storeId: string;
  taskId: string;
  statusUrl: string;
}

interface RecallResponse {
  storeId: string;
  items: DocumentSnippet[];
}

interface ChatSessionApi {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

interface ChatSessionListResponse {
  items: ChatSessionApi[];
  page: number;
  pageSize: number;
  total: number;
}

interface ChatSessionDetailResponse {
  session: ChatSessionApi;
  messages: ChatMessageApi[];
}

interface ChatMessageApi {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  citations: DocumentSnippet[];
}

interface ChatMessageResponse {
  sessionId: string;
  message: ChatMessageApi;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations: DocumentSnippet[];
}

interface ActiveVectorStore {
  id: string;
  name: string;
  config: VectorStoreConfig;
  createdAt: string;
  updatedAt: string;
  documentTaskId: string;
}

interface DocumentTaskResponse {
  taskId: string;
  status: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  message?: string | null;
  createdAt: string;
  updatedAt: string;
}

interface SelectedDocState {
  doc: DocumentSnippet;
  index: number;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8002/api/v1').replace(/\/$/, '');

const formatTimestamp = (date: Date) => {
  const weekday = date.toLocaleDateString('zh-CN', { weekday: 'short' });
  const normalizedWeekday = weekday.replace('周', '星期');
  const datePart = date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
  const time = date
    .toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    .replace(/^24:/, '00:');
  return `${normalizedWeekday} ${datePart} ${time}`;
};

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const buildUrl = (path: string) => {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  if (path.startsWith('/')) {
    return `${API_BASE_URL}${path}`;
  }
  return `${API_BASE_URL}/${path}`;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isFormData = init.body instanceof FormData;
  const headers = new Headers(init.headers ?? {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (!isFormData && init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(buildUrl(path), { ...init, headers });
  const contentType = response.headers.get('content-type') ?? '';
  const rawText = await response.text();
  const isJson = contentType.includes('application/json');
  let parsed: unknown = null;
  if (isJson && rawText) {
    try {
      parsed = JSON.parse(rawText);
    } catch (error) {
      console.warn('JSON parse failed', error);
    }
  }

  if (!response.ok) {
    let message = `请求失败: ${response.status}`;
    if (parsed && typeof parsed === 'object' && parsed !== null) {
      const detail = (parsed as Record<string, unknown>).detail;
      const msg = (parsed as Record<string, unknown>).message;
      if (typeof detail === 'string' && detail) {
        message = detail;
      } else if (typeof msg === 'string' && msg) {
        message = msg;
      } else if (detail && typeof detail === 'object') {
        message = JSON.stringify(detail);
      }
    } else if (rawText) {
      message = rawText;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!isJson) {
    return rawText as unknown as T;
  }

  return (parsed ?? {}) as T;
}

const getJson = <T,>(path: string) => request<T>(path);

const postJson = <T,>(path: string, body: unknown, init: RequestInit = {}) =>
  request<T>(path, {
    ...init,
    method: 'POST',
    body: JSON.stringify(body),
  });

const deleteRequest = (path: string) => request<void>(path, { method: 'DELETE' });

const normalizeSession = (session: ChatSessionApi): ChatSessionApi => ({
  ...session,
  title: session.title || '未命名会话',
});

const convertMessage = (message: ChatMessageApi): ChatMessage => ({
  id: message.id,
  role: message.role === 'assistant' ? 'assistant' : 'user',
  content: message.content,
  timestamp: formatTimestamp(new Date(message.timestamp)),
  citations: message.citations ?? [],
});

const waitForVectorStoreReady = async (storeId: string): Promise<ActiveVectorStore> => {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const store = await getJson<VectorStoreResponse>(`/vector-stores/${storeId}`);
    if (store.status === 'ready') {
      return {
        id: store.id,
        name: store.name,
        config: store.config,
        createdAt: store.createdAt,
        updatedAt: store.updatedAt,
        documentTaskId: store.documentTaskId,
      };
    }
    if (store.status === 'failed') {
      throw new Error(store.failureReason ?? '向量库构建失败，请检查日志');
    }
    await sleep(800);
  }
  throw new Error('向量库仍在构建中，请稍后重试');
};

const App = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileName, setSelectedFileName] = useState('');
  const [documentTask, setDocumentTask] = useState<DocumentTaskResponse | null>(null);
  const [vectorConfig, setVectorConfig] = useState<VectorStoreConfig>({
    name: 'AI 知识库',
    chunkSize: 2048,
    overlap: 128,
    topK: 3,
  });
  const [vectorStore, setVectorStore] = useState<ActiveVectorStore | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [processingState, setProcessingState] = useState(false);
  const [processingMessage, setProcessingMessage] = useState('');
  const [resultModal, setResultModal] = useState<'success' | 'fail' | null>(null);
  const [resultMessage, setResultMessage] = useState('');
  const [recallQuery, setRecallQuery] = useState('');
  const [isRecalling, setIsRecalling] = useState(false);
  const [recallResults, setRecallResults] = useState<DocumentSnippet[]>([]);
  const [sessions, setSessions] = useState<ChatSessionApi[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messagesBySession, setMessagesBySession] = useState<Record<string, ChatMessage[]>>({});
  const [chatInput, setChatInput] = useState('');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<SelectedDocState | null>(null);

  const activeMessages = useMemo(
    () => (activeSessionId ? messagesBySession[activeSessionId] ?? [] : []),
    [activeSessionId, messagesBySession],
  );

  useEffect(() => {
    void loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeSessionId && !messagesBySession[activeSessionId]) {
      void loadSessionMessages(activeSessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  useEffect(() => {
    if (!messagesContainerRef.current) {
      return;
    }
    messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
  }, [activeMessages]);

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const data = await getJson<ChatSessionListResponse>('/chat/sessions?page=1&page_size=50');
      const ordered = data.items
        .map(normalizeSession)
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
      setSessions(ordered);
      if (!activeSessionId && ordered.length > 0) {
        setActiveSessionId(ordered[0].id);
      }
    } catch (error) {
      console.error('加载会话列表失败', error);
    } finally {
      setLoadingSessions(false);
    }
  };

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const data = await getJson<ChatSessionDetailResponse>(`/chat/sessions/${sessionId}`);
      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId]: data.messages.map(convertMessage),
      }));
    } catch (error) {
      console.error('加载会话详情失败', error);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    if (!messagesBySession[sessionId]) {
      void loadSessionMessages(sessionId);
    }
  };

  const createSession = async (title?: string) => {
    const payload = title ? { title } : {};
    const session = await postJson<ChatSessionApi>('/chat/sessions', payload);
    const normalized = normalizeSession(session);
    setSessions((prev) => [normalized, ...prev.filter((item) => item.id !== normalized.id)]);
    setMessagesBySession((prev) => ({
      ...prev,
      [normalized.id]: prev[normalized.id] ?? [],
    }));
    return normalized;
  };

  const handleDeleteConversation = async (sessionId: string) => {
    try {
      await deleteRequest(`/chat/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((session) => session.id !== sessionId));
      setMessagesBySession((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        return next;
      });
      if (activeSessionId === sessionId) {
        setActiveSessionId((prev) => {
          const remaining = sessions.filter((session) => session.id !== sessionId);
          return remaining.length > 0 ? remaining[0].id : null;
        });
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '删除会话失败，请稍后再试');
    }
  };

  const handleStartConversation = async () => {
    try {
      const timestamp = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
      const session = await createSession(`新的对话 ${timestamp}`);
      setActiveSessionId(session.id);
      setChatInput('');
      setRecallResults([]);
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '创建会话失败，请稍后再试');
    }
  };

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = chatInput.trim();
    if (!content) {
      return;
    }

    setIsSendingMessage(true);
    let sessionId = activeSessionId;
    try {
      if (!sessionId) {
        const session = await createSession();
        sessionId = session.id;
        setActiveSessionId(sessionId);
      }

      const userMessage: ChatMessage = {
        id: `local-${Date.now()}`,
        role: 'user',
        content,
        timestamp: formatTimestamp(new Date()),
        citations: [],
      };

      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId!]: [...(prev[sessionId!] ?? []), userMessage],
      }));
      setChatInput('');

      const response = await postJson<ChatMessageResponse>(`/chat/sessions/${sessionId!}/messages`, {
        message: content,
        vectorStoreId: vectorStore?.id,
      });

      const assistantMessage = convertMessage(response.message);
      setMessagesBySession((prev) => ({
        ...prev,
        [sessionId!]: [...(prev[sessionId!] ?? []), assistantMessage],
      }));
      setRecallResults(assistantMessage.citations ?? []);
      setSelectedDoc(null);
      void loadSessions();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '发送消息失败，请稍后再试');
      if (sessionId) {
        await loadSessionMessages(sessionId);
      }
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleFileInputChange = (event: FormEvent<HTMLInputElement>) => {
    const file = (event.currentTarget.files && event.currentTarget.files[0]) ?? null;
    setSelectedFile(file);
    setSelectedFileName(file?.name ?? '');
  };

  const handleConfirmFile = async () => {
    if (!selectedFile) {
      window.alert('请先选择要上传的文件');
      return;
    }

    try {
      setProcessingMessage('正在上传文档并进行校验...');
      setProcessingState(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      const response = await request<DocumentTaskResponse>('/documents', {
        method: 'POST',
        body: formData,
      });
      setDocumentTask(response);
      setProcessingState(false);
      setProcessingMessage('');
      setUploadModalOpen(false);
      setConfigModalOpen(true);
      setResultModal(null);
      setResultMessage('');
    } catch (error) {
      setProcessingState(false);
      setProcessingMessage('');
      window.alert(error instanceof Error ? error.message : '文档上传失败，请稍后再试');
    }
  };

  const handleConfigSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!documentTask) {
      window.alert('请先上传并通过校验的文档');
      return;
    }

    setConfigModalOpen(false);
    setProcessingMessage('向量库构建中，请稍候...');
    setProcessingState(true);
    setResultModal(null);
    setResultMessage('');

    try {
      const createResponse = await postJson<CreateVectorStoreResponse>('/vector-stores', {
        documentTaskId: documentTask.taskId,
        config: vectorConfig,
      });
      const store = await waitForVectorStoreReady(createResponse.storeId);
      setVectorStore(store);
      setResultModal('success');
      setResultMessage('知识库构建完成，现在可以进行检索与对话引用');
      setRecallResults([]);
      setRecallQuery('');
    } catch (error) {
      setResultModal('fail');
      setResultMessage(error instanceof Error ? error.message : '知识库构建失败，请稍后再试');
    } finally {
      setProcessingState(false);
      setProcessingMessage('');
    }
  };

  const handleRecallSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!vectorStore) {
      window.alert('请先构建知识库后再进行检索');
      return;
    }
    if (!recallQuery.trim()) {
      setRecallResults([]);
      return;
    }

    try {
      setIsRecalling(true);
      const data = await postJson<RecallResponse>(`/vector-stores/${vectorStore.id}/recall`, {
        query: recallQuery.trim(),
        topK: vectorStore.config.topK,
        withContent: true,
      });
      setRecallResults(data.items);
      if (data.items.length === 0) {
        setResultModal('fail');
        setResultMessage('未检索到相关片段，可以尝试调整关键词或重新构建知识库');
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '检索失败，请稍后再试');
    } finally {
      setIsRecalling(false);
    }
  };

  const knowledgePanelContent = vectorStore ? (
    <div className="knowledge-panel__body">
      <div className="knowledge-panel__header">
        <span className="tag">当前知识库</span>
        <h3>{vectorStore.name}</h3>
        <p>
          切片 {vectorStore.config.chunkSize} tokens · 重叠 {vectorStore.config.overlap} tokens · Top-K{' '}
          {vectorStore.config.topK}
        </p>
        <p className="knowledge-panel__meta">
          构建时间：{formatTimestamp(new Date(vectorStore.createdAt))}
        </p>
      </div>

      <div className="recall__head">
        <h4>知识库检索</h4>
        <p>支持关键词检索，也可以在对话时引用自动召回的片段</p>
      </div>

      <form className="recall__form" onSubmit={handleRecallSubmit}>
        <input
          placeholder="请输入要检索的关键词"
          value={recallQuery}
          onChange={(event) => setRecallQuery(event.target.value)}
          disabled={isRecalling}
        />
        <div className="recall__formActions">
          <button type="submit" disabled={isRecalling}>
            {isRecalling ? '检索中...' : '检索'}
          </button>
        </div>
      </form>

      <div className="recall__results">
        {recallResults.length === 0 ? (
          <div className="recall__empty">暂无检索结果，尝试换一个关键词或重新索引文档</div>
        ) : (
          recallResults.map((doc, index) => (
            <button
              key={doc.id}
              type="button"
              className="recall__item"
              onClick={() => setSelectedDoc({ doc, index: index + 1 })}
            >
              <div className="recall__itemHeader">
                <span className="recall__itemIndex">片段 {index + 1}</span>
                <span className="recall__itemScore">相似度 {doc.similarity.toFixed(2)}</span>
              </div>
              <span className="recall__itemTitle">{doc.title || '未命名片段'}</span>
              <span className="recall__itemSource">{(doc.metadata?.source as string) ?? '未标注来源'}</span>
              <p>{doc.content}</p>
            </button>
          ))
        )}
      </div>
    </div>
  ) : (
    <div className="knowledge-panel__empty">
      <h3>尚未构建知识库</h3>
      <p>上传文档并完成向量化构建后，即可在此检索和引用知识片段。</p>
      <button type="button" onClick={() => setUploadModalOpen(true)}>
        立即上传文档
      </button>
    </div>
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__brand">CodeX RAG</div>
        <div className="topbar__title">知识增强对话系统</div>
        <div className="topbar__cta">
          <button type="button" onClick={() => setUploadModalOpen(true)}>
            上传文档构建知识库
          </button>
        </div>
      </header>

      <main className="app__body">
        <section className="chat-panel">
          <div className="chat-panel__header">
            <div>
              <h2>智能对话助手</h2>
              <p>支持引用知识库的检索结果，提供更加可靠的回答</p>
            </div>
            <div className="chat-panel__actions">
              <span className="secondary-tag">
                {vectorStore ? `已连接知识库：${vectorStore.name}` : '知识库未构建'}
              </span>
              <button type="button" onClick={handleStartConversation}>
                新建对话
              </button>
            </div>
          </div>

          <div className="chat-panel__content">
            <aside className="chat-tabs">
              <div className="chat-tabs__list">
                {loadingSessions ? (
                  <div className="chat-tabs__empty">
                    <p>正在加载会话...</p>
                  </div>
                ) : sessions.length === 0 ? (
                  <div className="chat-tabs__empty">
                    <p>暂无会话记录</p>
                    <button type="button" onClick={handleStartConversation}>
                      开始新的对话
                    </button>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      className={`chat-tab${activeSessionId === session.id ? ' active' : ''}`}
                      onClick={() => handleSelectSession(session.id)}
                    >
                      <div className="chat-tab__info">
                        <span className="chat-tab__title">{session.title}</span>
                        <span className="chat-tab__time">
                          更新时间：{formatTimestamp(new Date(session.updatedAt))}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="chat-tab__delete"
                        aria-label="删除会话"
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleDeleteConversation(session.id);
                        }}
                      >
                        ×
                      </button>
                    </button>
                  ))
                )}
              </div>
            </aside>

            <div className="chat-panel__conversation">
              <div className="chat-panel__messages" ref={messagesContainerRef}>
                {activeMessages.length === 0 ? (
                  <div className="chat-panel__empty">
                    <h4>{activeSessionId ? '暂无对话记录' : '点击右上角开始新的对话'}</h4>
                    <p>准备好问题后，输入框支持引用知识库的答案</p>
                  </div>
                ) : (
                  activeMessages.map((message) => (
                    <div key={message.id} className={`chat-message-row ${message.role}`}>
                      <div className={`chat-avatar ${message.role}`} aria-hidden="true">
                        {message.role === 'user' ? '问' : '答'}
                      </div>
                      <div className={`chat-message ${message.role}`}>
                        <div className="chat-message__meta">
                          <span>{message.role === 'user' ? '用户' : '助手'}</span>
                          <span className="timestamp">{message.timestamp}</span>
                        </div>
                        <p className="chat-message__content">{message.content}</p>
                        {message.citations.length > 0 && (
                          <div className="chat-message__citations">
                            引用片段：
                            {message.citations.map((doc, index) => (
                              <button
                                key={`${message.id}-citation-${index}`}
                                type="button"
                                onClick={() => setSelectedDoc({ doc, index: index + 1 })}
                              >
                                片段 {index + 1}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <form className="chat-panel__input" onSubmit={handleSendMessage}>
                <input
                  placeholder={
                    activeSessionId
                      ? '请输入问题，例如：构建向量库需要哪些步骤？'
                      : '请先创建一个对话，再开始提问'
                  }
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  disabled={isSendingMessage}
                />
                <button type="submit" disabled={isSendingMessage || !chatInput.trim()}>
                  {isSendingMessage ? '发送中...' : '发送'}
                </button>
              </form>
            </div>
          </div>
        </section>

        <section className="knowledge-panel">{knowledgePanelContent}</section>
      </main>

      <Modal isOpen={uploadModalOpen} title="上传文档" onClose={() => setUploadModalOpen(false)}>
        <div className="upload-modal">
          <p className="hint">一次上传一份文档，支持 .txt / .md / .pdf</p>
          <label className="file-picker">
            <input type="file" accept=".txt,.md,.pdf" onChange={handleFileInputChange} />
            <span>{selectedFileName || '选择文件'}</span>
          </label>
          <div className="modal__actions">
            <button className="secondary" type="button" onClick={() => setUploadModalOpen(false)}>
              取消
            </button>
            <button className="primary" type="button" onClick={() => void handleConfirmFile()}>
              下一步
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={configModalOpen}
        title="配置知识库参数"
        width="560px"
        onClose={() => setConfigModalOpen(false)}
      >
        <form className="config-form" onSubmit={handleConfigSubmit}>
          <div className="form-grid">
            <label>
              <span>知识库名称</span>
              <input
                value={vectorConfig.name}
                onChange={(event) => setVectorConfig((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="请输入知识库名称"
              />
            </label>
            <label>
              <span>切片最大长度（tokens）</span>
              <input
                type="number"
                min={256}
                max={4096}
                value={vectorConfig.chunkSize}
                onChange={(event) =>
                  setVectorConfig((prev) => ({ ...prev, chunkSize: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              <span>切片重叠（tokens）</span>
              <input
                type="number"
                min={0}
                max={512}
                value={vectorConfig.overlap}
                onChange={(event) =>
                  setVectorConfig((prev) => ({ ...prev, overlap: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              <span>召回 Top-K</span>
              <input
                type="number"
                min={1}
                max={10}
                value={vectorConfig.topK}
                onChange={(event) =>
                  setVectorConfig((prev) => ({ ...prev, topK: Number(event.target.value) }))
                }
              />
            </label>
          </div>

          <div className="modal__actions">
            <button className="secondary" type="button" onClick={() => setConfigModalOpen(false)}>
              取消
            </button>
            <button className="primary" type="submit">
              构建知识库
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={processingState} width="420px">
        <div className="processing">
          <div className="processing__spinner" />
          <p>{processingMessage || '正在处理，请稍后...'}</p>
        </div>
      </Modal>

      <Modal
        isOpen={Boolean(resultModal)}
        title={resultModal === 'success' ? '知识库已就绪' : '操作失败'}
        width="430px"
        onClose={() => setResultModal(null)}
      >
        <div className="result-modal">
          <p>{resultMessage || (resultModal === 'success' ? '操作成功' : '请稍后重试')}</p>
          <div className="modal__actions">
            <button className="primary" type="button" onClick={() => setResultModal(null)}>
              确定
            </button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={Boolean(selectedDoc)} width="640px" onClose={() => setSelectedDoc(null)}>
        {selectedDoc && (
          <div className="doc-detail">
            <header>
              <span>片段 {selectedDoc.index}</span>
              <span className="similarity">相似度 {(selectedDoc.doc.similarity ?? 0).toFixed(2)}</span>
            </header>
            <h4>{selectedDoc.doc.title || '未命名片段'}</h4>
            <p>{selectedDoc.doc.content}</p>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default App;
