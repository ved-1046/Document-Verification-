import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
    Bot,
    Send,
    Sparkles,
    UserRound,
    LoaderCircle,
    AlertTriangle,
    Shield,
    ArrowLeft,
    RefreshCw,
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { AssistantResponse, RequestSummary } from '../types';

interface ChatMessage {
    id: string;
    sender: 'user' | 'assistant';
    text: string;
    citations?: string[];
    mode?: string;
    timestamp: string;
}

function renderInlineFormatting(text: string) {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            const boldText = part.slice(2, -2);
            return (
                <strong key={index} className="font-semibold text-slate-900">
                    {boldText}
                </strong>
            );
        }
        if (part.startsWith('`') && part.endsWith('`')) {
            const codeText = part.slice(1, -1);
            return (
                <code key={index} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] font-semibold text-blue-700">
                    {codeText}
                </code>
            );
        }
        const clean = part.replace(/\*\*/g, '').replace(/^\*\s/, '');
        return <span key={index}>{clean}</span>;
    });
}

function FormattedAssistantAnswer({ text, citations }: { text: string; citations?: string[]; mode?: string }) {
    // Clean out raw diagnostic tokens or tags if any slipped through
    const cleanedText = text
        .replace(/<details>[\s\S]*?<\/details>/gi, '')
        .replace(/\*\*Deterministic fallback.*?\*\*/gi, '')
        .replace(/Deterministic fallback \(not an LLM response\)\.?/gi, '')
        .trim();

    const lines = cleanedText.split('\n');
    const elements: React.ReactNode[] = [];
    let currentBulletList: string[] = [];

    const flushBulletList = () => {
        if (currentBulletList.length > 0) {
            elements.push(
                <ul key={`list-${elements.length}`} className="my-2 space-y-1.5 pl-1">
                    {currentBulletList.map((item, idx) => {
                        const isIssue = /missing|failed|flag|differ|mismatch|error|unreadable/i.test(item);
                        return (
                            <li key={idx} className="flex items-start gap-2.5 text-xs text-slate-700">
                                <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${isIssue ? 'bg-amber-500' : 'bg-[#3478F6]'}`} />
                                <div className="leading-relaxed font-normal">{renderInlineFormatting(item)}</div>
                            </li>
                        );
                    })}
                </ul>
            );
            currentBulletList = [];
        }
    };

    lines.forEach((rawLine, lineIndex) => {
        const line = rawLine.trim();
        if (!line) {
            flushBulletList();
            return;
        }

        if (line.startsWith('⚠️') || line.toLowerCase().includes('attention notice') || line.toLowerCase().includes('document processing alert')) {
            flushBulletList();
            const cleanNotice = line.replace(/^(?:⚠️|\s)+/, '');
            elements.push(
                <div key={`alert-${lineIndex}`} className="my-2.5 rounded-xl border border-amber-200 bg-amber-50/90 p-3 shadow-2xs">
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                        <div className="text-xs text-amber-900 leading-relaxed font-medium">
                            {renderInlineFormatting(cleanNotice)}
                        </div>
                    </div>
                </div>
            );
            return;
        }

        if (line.startsWith('- ') || line.startsWith('* ')) {
            currentBulletList.push(line.substring(2).trim());
            return;
        }

        flushBulletList();

        if (line.endsWith(':') || line.startsWith('###') || line.startsWith('##')) {
            const headingText = line.replace(/^#+\s*/, '').replace(/:$/, '');
            elements.push(
                <h3 key={`head-${lineIndex}`} className="mt-3 mb-1 text-xs font-bold text-slate-900 uppercase tracking-wider">
                    {renderInlineFormatting(headingText)}
                </h3>
            );
            return;
        }

        elements.push(
            <p key={`p-${lineIndex}`} className="my-1 text-xs text-slate-800 leading-relaxed font-normal">
                {renderInlineFormatting(line)}
            </p>
        );
    });

    flushBulletList();

    return (
        <div className="space-y-2">
            <div className="text-xs leading-relaxed text-slate-800">
                {elements}
            </div>

            {/* Citations */}
            {citations && citations.length > 0 && (
                <div className="mt-3 border-t border-slate-100 pt-2.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                        Verified Evidence Citations
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                        {citations.map((c) => (
                            <span key={c} className="rounded-md bg-blue-50 text-[#3478F6] border border-blue-200 px-2 py-0.5 text-[10px] font-semibold">
                                {c}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function AIAssistantPage() {
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const queryRequestId = searchParams.get('requestId') || searchParams.get('request_id') || '';

    const [requestId, setRequestId] = useState(queryRequestId);
    const [question, setQuestion] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [userRequests, setUserRequests] = useState<RequestSummary[]>([]);

    const userRole = user?.role || 'submitter';

    // Role-specific badge and styling
    const roleConfigMap: Record<string, { title: string; badgeBg: string; description: string }> = {
        submitter: {
            title: 'Submitter Guidance',
            badgeBg: 'bg-teal-50 border-teal-200 text-[#0F9D8A]',
            description: 'Answers explain verification checks, missing documents, and what you should correct.',
        },
        reviewer: {
            title: 'Reviewer Investigation Station',
            badgeBg: 'bg-blue-50 border-blue-200 text-[#3478F6]',
            description: 'Answers cross-examine claim values against extracted receipt tokens and rule flags.',
        },
        approver: {
            title: 'Approver Decision Support',
            badgeBg: 'bg-violet-50 border-violet-200 text-[#7656D6]',
            description: 'Executive summaries, reviewer notes, and key factors to weigh before your final decision.',
        },
    };
    const roleConfig = roleConfigMap[userRole] || roleConfigMap.submitter;

    // Load user's accessible claims
    useEffect(() => {
        api.get<RequestSummary[]>('/requests')
            .then((response) => {
                if (Array.isArray(response.data)) {
                    setUserRequests(response.data);
                    if (!queryRequestId && response.data.length > 0) {
                        setRequestId(String(response.data[0].id));
                    }
                }
            })
            .catch(() => {});
    }, [queryRequestId]);

    // Load suggested questions when active claim changes
    useEffect(() => {
        if (!requestId) return;
        api.get<{ questions: string[] }>(`/assistant/suggested-questions?request_id=${requestId}`)
            .then((res) => {
                if (res.data?.questions) {
                    setSuggestedQuestions(res.data.questions);
                }
            })
            .catch(() => {
                // Fallback default suggestions
                if (userRole === 'submitter') {
                    setSuggestedQuestions([
                        'What do I need to fix on this claim?',
                        'Why was my claim flagged?',
                        'Which documents or fields are missing?',
                        'What is the current status of my claim?',
                    ]);
                } else if (userRole === 'reviewer') {
                    setSuggestedQuestions([
                        'Summarise all verification findings and flags.',
                        'Compare the claimed details with the receipt evidence.',
                        'What questions or corrections should I ask the submitter?',
                        'Are there any unreadable documents or missing fields?',
                    ]);
                } else {
                    setSuggestedQuestions([
                        'Summarise this claim and the reviewer’s findings.',
                        'Are there any unresolved discrepancies or risk factors?',
                        'What factors should I consider before deciding?',
                        'Is all required evidence present and verified?',
                    ]);
                }
            });
    }, [requestId, userRole]);

    async function handleAsk(event?: FormEvent, customQ?: string) {
        if (event) event.preventDefault();
        const queryText = (customQ || question).trim();
        if (!queryText || !requestId || loading) return;

        setError(null);
        setLoading(true);

        const userMsg: ChatMessage = {
            id: `usr-${Date.now()}`,
            sender: 'user',
            text: queryText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setMessages((prev) => [...prev, userMsg]);
        setQuestion('');

        try {
            const response = await api.post<AssistantResponse>('/assistant/ask', {
                request_id: Number(requestId),
                question: queryText,
            });

            const aiMsg: ChatMessage = {
                id: `ai-${Date.now()}`,
                sender: 'assistant',
                text: response.data.answer,
                citations: response.data.citations,
                mode: response.data.mode,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            };

            setMessages((prev) => [...prev, aiMsg]);
        } catch (err) {
            const failure = err as { response?: { status?: number; data?: { detail?: string } } };
            const status = failure.response?.status;
            const detail = failure.response?.data?.detail;

            if (status === 403) {
                setError('Access denied. You can only query claims assigned to you or owned by you.');
            } else if (status === 404) {
                setError('Claim not found. Please choose an authorized claim.');
            } else if (detail) {
                setError(detail);
            } else {
                setError('The assistant is temporarily unavailable. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    }

    const activeClaim = userRequests.find((r) => String(r.id) === String(requestId));

    return (
        <div className="page-wrap mx-auto max-w-4xl space-y-5">
            {/* Header */}
            <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                    <div className={`mb-1.5 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${roleConfig.badgeBg}`}>
                        <Sparkles className="h-3 w-3" />
                        {roleConfig.title}
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                        DocuVerify AI Assistant
                    </h1>
                    <p className="mt-0.5 text-xs text-slate-500">
                        {roleConfig.description}
                    </p>
                </div>

                {activeClaim && (
                    <Link
                        to={`/requests/${activeClaim.id}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 transition"
                    >
                        <ArrowLeft className="h-3.5 w-3.5" />
                        <span>Return to Claim #{activeClaim.request_number}</span>
                    </Link>
                )}
            </header>

            {/* Approver Responsibility Advisory (Shown only for Approver) */}
            {userRole === 'approver' && (
                <div className="rounded-xl border border-violet-200 bg-violet-50/70 p-3.5 flex items-start gap-2.5 text-xs text-violet-900">
                    <Shield className="h-4 w-4 text-[#7656D6] shrink-0 mt-0.5" />
                    <div>
                        <strong className="font-bold">Executive Decision Support Mode:</strong> The assistant highlights claim evidence, verified receipt totals, and reviewer notes. As the designated Approver, final approval authority and responsibility rests exclusively with you.
                    </div>
                </div>
            )}

            {/* Suggested Question Chips */}
            {suggestedQuestions.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-semibold text-slate-400">Suggested inquiries:</span>
                    {suggestedQuestions.map((qText) => (
                        <button
                            key={qText}
                            type="button"
                            onClick={() => handleAsk(undefined, qText)}
                            disabled={loading || !requestId}
                            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 font-medium hover:border-[#3478F6] hover:text-[#3478F6] transition shadow-2xs disabled:opacity-50"
                        >
                            {qText}
                        </button>
                    ))}
                </div>
            )}

            {/* Chat Container */}
            <section className="card flex flex-col overflow-hidden border-slate-200 shadow-sm min-h-[520px]">
                {/* Chat Stream Surface */}
                <div className="flex flex-1 flex-col gap-4 bg-[#F5F7FB] p-6 overflow-y-auto max-h-[580px]">
                    {messages.length === 0 && !loading && (
                        <div className="m-auto max-w-sm text-center py-12 space-y-2">
                            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-[#3478F6] shadow-sm border border-slate-200 mb-2">
                                <Bot className="h-6 w-6" />
                            </span>
                            <h2 className="text-sm font-bold text-slate-900">How can I help you with this claim?</h2>
                            <p className="text-xs text-slate-500 leading-relaxed">
                                Select a claim below or click one of the suggested questions. DocuVerify AI will analyze the uploaded documents and rule results.
                            </p>
                        </div>
                    )}

                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                        >
                            {msg.sender === 'user' ? (
                                <div className="max-w-[85%] rounded-2xl rounded-br-xs bg-[#14213D] p-4 text-xs leading-relaxed text-white shadow-sm">
                                    <div className="mb-1 flex items-center justify-end gap-1.5 text-[9px] font-bold text-blue-300">
                                        <UserRound className="h-3 w-3" /> You · {msg.timestamp}
                                    </div>
                                    <p className="font-medium">{msg.text}</p>
                                </div>
                            ) : (
                                <div className="max-w-[92%] rounded-2xl rounded-bl-xs border border-slate-200 bg-white p-5 shadow-xs space-y-2.5">
                                    <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2">
                                        <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
                                            <Bot className="h-4 w-4 text-[#3478F6]" />
                                            <span>DocuVerify AI · Grounded Evidence</span>
                                        </div>
                                        <span className="text-[10px] text-slate-400 font-medium">
                                            {msg.timestamp}
                                        </span>
                                    </div>
                                    <FormattedAssistantAnswer
                                        text={msg.text}
                                        citations={msg.citations}
                                        mode={msg.mode}
                                    />
                                </div>
                            )}
                        </div>
                    ))}

                    {loading && (
                        <div className="flex max-w-[85%] items-center gap-3 rounded-2xl rounded-bl-xs border border-slate-200 bg-white p-4 text-xs font-medium text-slate-600 shadow-xs">
                            <LoaderCircle className="h-4 w-4 animate-spin text-[#3478F6]" />
                            <span>Analyzing verified documents, rule checks, and audit history…</span>
                        </div>
                    )}

                    {error && (
                        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-700 font-medium flex items-center justify-between">
                            <span>{error}</span>
                            <button
                                type="button"
                                onClick={() => handleAsk()}
                                className="ml-3 inline-flex items-center gap-1 font-bold text-red-800 underline hover:no-underline"
                            >
                                <RefreshCw className="h-3 w-3" /> Retry
                            </button>
                        </div>
                    )}
                </div>

                {/* Input Bar with Claim Selector */}
                <form className="border-t border-slate-200 bg-white p-4 space-y-3" onSubmit={handleAsk}>
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                        {/* Claim Selector */}
                        <div className="sm:w-60 shrink-0">
                            <label htmlFor="request-id" className="sr-only">Claim</label>
                            {userRequests.length > 0 ? (
                                <select
                                    id="request-id"
                                    aria-label="Select Claim"
                                    className="form-input text-xs py-2 bg-slate-50 font-medium w-full"
                                    value={requestId}
                                    onChange={(e) => {
                                        setRequestId(e.target.value);
                                        setMessages([]);
                                        setError(null);
                                    }}
                                >
                                    {userRequests.map((r) => (
                                        <option key={r.id} value={r.id}>
                                            #{r.request_number} · {r.title}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    id="request-id"
                                    type="number"
                                    min="1"
                                    className="form-input text-xs py-2"
                                    placeholder="Claim ID #"
                                    value={requestId}
                                    onChange={(e) => setRequestId(e.target.value)}
                                    required
                                />
                            )}
                        </div>

                        {/* Question Input */}
                        <div className="flex-1 flex gap-2">
                            <input
                                id="question"
                                type="text"
                                className="form-input text-xs py-2 flex-1"
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                placeholder="Ask about claim amounts, receipt tokens, or verification findings…"
                                required
                            />
                            <button
                                type="submit"
                                disabled={loading || !requestId || !question.trim()}
                                className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 shrink-0"
                            >
                                <Send className="h-3.5 w-3.5" />
                                <span>{loading ? 'Asking…' : 'Ask'}</span>
                            </button>
                        </div>
                    </div>
                </form>
            </section>
        </div>
    );
}
