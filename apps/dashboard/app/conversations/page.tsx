'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, RefreshCw, Phone, Clock, MessageSquare, Wrench,
  User, Bot, ChevronRight, AlertCircle, Wifi, WifiOff,
  Download, Hash, Globe, CheckCircle, XCircle,
} from 'lucide-react';

interface ConversationSummary {
  id: string;
  call_id: number;
  status: string;
  quality_score: number | null;
  phone: string;
  duration_seconds: number;
  language: string;
  transcript_count: number;
  tool_count: number;
  outcome: string;
  sentiment: string;
  started_at: string;
  ended_at: string;
}

interface TranscriptEntry {
  role: string;
  content: string;
  timestamp?: string;
  name?: string;
  tool_name?: string;
  tool_input?: any;
  tool_output?: any;
}

interface ConversationDetail extends ConversationSummary {
  transcript: TranscriptEntry[];
  cost?: number;
  model?: string;
  error_message?: string;
}

function formatDuration(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return ts;
  }
}

function qualityColor(score: number | null): string {
  if (score === null) return 'text-brand-muted';
  const pct = score <= 1 ? score * 100 : score;
  if (pct >= 80) return 'text-emerald-400';
  if (pct >= 60) return 'text-amber-400';
  return 'text-brand-salmon';
}

function qualityDisplay(score: number | null): string {
  if (score === null) return 'N/A';
  if (score <= 1) return `${Math.round(score * 100)}%`;
  return `${Math.round(score)}%`;
}

function sentimentBadge(s: string) {
  const map: Record<string, string> = {
    positive: 'bg-emerald-500/20 text-emerald-400',
    neutral: 'bg-cyan-500/20 text-cyan-400',
    negative: 'bg-red-500/20 text-brand-salmon',
    mixed: 'bg-amber-500/20 text-amber-400',
  };
  return map[s?.toLowerCase()] || 'bg-brand-cream text-brand-slate';
}

function statusIcon(status: string) {
  if (status === 'completed') return <CheckCircle size={12} className="text-emerald-400" />;
  if (status === 'failed') return <XCircle size={12} className="text-brand-salmon" />;
  return <AlertCircle size={12} className="text-amber-400" />;
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const transcriptEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 400);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ limit: '50', offset: '0' });
    if (debouncedSearch) params.set('search', debouncedSearch);
    const resp = await fetch(`/api/dashboard/conversations?${params}`);
    const result = await resp.json();
    if (result.data) {
      setConversations(result.data);
      setTotal(result.total || result.data.length);
      setIsLive(true);
    } else {
      setError(result.error || 'Failed to load');
      setIsLive(false);
    }
    setLoading(false);
  }, [debouncedSearch]);

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 30000);
    return () => clearInterval(interval);
  }, [loadConversations]);

  const loadDetail = useCallback(async (callSid: string) => {
    if (selectedId === callSid) {
      setSelectedId(null);
      setDetail(null);
      return;
    }
    setSelectedId(callSid);
    setDetailLoading(true);
    setDetail(null);
    const resp2 = await fetch(`/api/dashboard/conversations/${callSid}`);
    const result2 = await resp2.json();
    if (result2.data) {
      setDetail(result2.data);
    } else {
      const summary = conversations.find((c) => c.id === callSid);
      if (summary) setDetail({ ...summary, transcript: [] });
    }
    setDetailLoading(false);
  }, [selectedId, conversations]);

  useEffect(() => {
    if (detail?.transcript?.length) {
      transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [detail]);

  const exportDetail = () => {
    if (!detail) return;
    const blob = new Blob([JSON.stringify(detail, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${detail.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-transparent p-6">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-brand-navy mb-1">
              Conversations
            </h1>
            <p className="text-brand-slate text-sm">
              {isLive ? (
                <span className="flex items-center gap-2">
                  <Wifi size={13} className="text-emerald-400" />
                  Live &middot; {total} conversations
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <WifiOff size={13} className="text-amber-400" />
                  {error || 'Connecting\u2026'}
                </span>
              )}
            </p>
          </div>
          <button
            onClick={loadConversations}
            disabled={loading}
            className="glass-hover px-3 py-2 rounded-lg text-sm text-brand-pink flex items-center gap-2"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Main layout: list + detail */}
        <div className="flex gap-6 items-start" style={{ minHeight: 'calc(100vh - 160px)' }}>
          {/* Left: conversation list */}
          <div className="w-[440px] shrink-0 flex flex-col gap-4">
            {/* Search */}
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-muted" />
              <input
                type="text"
                placeholder="Search by ID, phone, outcome\u2026"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2.5 bg-white shadow-sm border border-brand-cream rounded-lg text-brand-navy text-sm placeholder-zinc-500 focus:outline-none focus:border-accent/50 transition-colors"
              />
            </div>

            {/* List */}
            <div className="space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 240px)' }}>
              {loading && conversations.length === 0 && (
                <div className="glass p-8 rounded-lg text-center">
                  <RefreshCw size={20} className="mx-auto text-brand-muted animate-spin mb-2" />
                  <p className="text-brand-muted text-sm">Loading&hellip;</p>
                </div>
              )}

              {!loading && conversations.length === 0 && (
                <div className="glass p-8 rounded-lg text-center">
                  <AlertCircle size={28} className="mx-auto text-brand-muted mb-2" />
                  <p className="text-brand-slate text-sm">
                    {error ? error : 'No conversations found'}
                  </p>
                </div>
              )}

              {conversations.map((conv) => {
                const isActive = selectedId === conv.id;
                return (
                  <button
                    key={conv.id}
                    onClick={() => loadDetail(conv.id)}
                    className={`w-full text-left p-4 rounded-lg border transition-all ${
                      isActive
                        ? 'bg-[#ecd8d3] border-brand-pink/40'
                        : 'bg-white/50 shadow-sm border-brand-cream hover:border-[#dfcdc7] hover:bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-brand-navy truncate max-w-[200px]">
                        {conv.id}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {statusIcon(conv.status)}
                        <span className="text-[11px] text-brand-slate uppercase">
                          {conv.status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-brand-muted mb-2">
                      <span className="flex items-center gap-1">
                        <Clock size={11} />
                        {formatDuration(conv.duration_seconds)}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare size={11} />
                        {conv.transcript_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <Wrench size={11} />
                        {conv.tool_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <Globe size={11} />
                        {conv.language.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {conv.outcome && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-brand-pink border border-brand-pink/20">
                          {conv.outcome.replace(/_/g, ' ')}
                        </span>
                      )}
                      {conv.sentiment && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full ${sentimentBadge(conv.sentiment)}`}>
                          {conv.sentiment}
                        </span>
                      )}
                      {conv.quality_score !== null && (
                        <span className={`text-[10px] font-mono ml-auto ${qualityColor(conv.quality_score)}`}>
                          Q {qualityDisplay(conv.quality_score)}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right: detail panel */}
          <div className="flex-1 min-w-0">
            {!selectedId && (
              <div className="glass rounded-lg p-12 text-center" style={{ minHeight: '400px' }}>
                <MessageSquare size={40} className="mx-auto text-zinc-700 mb-3" />
                <p className="text-brand-muted text-sm">
                  Select a conversation to view its transcript
                </p>
              </div>
            )}

            {selectedId && detailLoading && (
              <div className="glass rounded-lg p-12 text-center" style={{ minHeight: '400px' }}>
                <RefreshCw size={24} className="mx-auto text-brand-muted animate-spin mb-3" />
                <p className="text-brand-muted text-sm">Loading conversation&hellip;</p>
              </div>
            )}

            {selectedId && !detailLoading && detail && (
              <div className="glass rounded-lg overflow-hidden">
                {/* Detail header */}
                <div className="p-5 border-b border-brand-cream">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-brand-navy font-semibold text-sm flex items-center gap-2">
                      <Hash size={14} className="text-brand-pink" />
                      <span className="font-mono">{detail.id}</span>
                    </h2>
                    <button
                      onClick={exportDetail}
                      className="glass-hover px-3 py-1.5 rounded-md text-xs text-brand-pink flex items-center gap-1.5"
                    >
                      <Download size={13} />
                      Export
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                    <DetailStat label="Status" value={detail.status} className="uppercase" />
                    <DetailStat label="Duration" value={formatDuration(detail.duration_seconds)} />
                    <DetailStat label="Phone" value={detail.phone || 'unknown'} mono />
                    <DetailStat
                      label="Quality"
                      value={qualityDisplay(detail.quality_score)}
                      className={qualityColor(detail.quality_score)}
                    />
                    <DetailStat label="Outcome" value={detail.outcome?.replace(/_/g, ' ') || '\u2014'} />
                    <DetailStat label="Sentiment" value={detail.sentiment || '\u2014'} />
                    {detail.cost && (
                      <DetailStat label="Cost" value={`€${(typeof detail.cost === "object" ? detail.cost.total_usd : detail.cost || 0).toFixed(4)}`} />
                    )}
                    <DetailStat label="Messages" value={String(detail.transcript_count)} />
                    <DetailStat label="Tool Calls" value={String(detail.tool_count)} />
                    <DetailStat label="Language" value={detail.language.toUpperCase()} />
                    <DetailStat label="Started" value={formatTime(detail.started_at)} />
                    <DetailStat label="Ended" value={detail.ended_at ? formatTime(detail.ended_at) : '\u2014'} />
                  </div>
                </div>

                {/* Transcript */}
                <div
                  className="p-5 overflow-y-auto space-y-3"
                  style={{ maxHeight: 'calc(100vh - 380px)' }}
                >
                  {(!detail.transcript || detail.transcript.length === 0) && (
                    <p className="text-brand-muted text-sm text-center py-8">
                      No transcript available for this conversation.
                    </p>
                  )}

                  {detail.transcript?.map((entry, idx) => (
                    <TranscriptBubble key={idx} entry={entry} />
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailStat({
  label,
  value,
  mono,
  className = '',
}: {
  label: string;
  value: string;
  mono?: boolean;
  className?: string;
}) {
  return (
    <div>
      <p className="text-[10px] text-brand-muted mb-0.5">{label}</p>
      <p className={`text-sm text-brand-navy font-medium truncate ${mono ? 'font-mono' : ''} ${className}`}>
        {value}
      </p>
    </div>
  );
}

function TranscriptBubble({ entry }: { entry: TranscriptEntry }) {
  const role = (entry.role || '').toLowerCase();

  if (role === 'user' || role === 'human' || role === 'customer') {
    return (
      <div className="flex gap-3 max-w-[85%]">
        <div className="w-7 h-7 rounded-full bg-brand-cream border border-[#e8d8d2] flex items-center justify-center shrink-0 mt-0.5">
          <User size={13} className="text-brand-slate" />
        </div>
        <div>
          <p className="text-[10px] text-brand-muted mb-1">
            User
            {entry.timestamp && <span className="ml-2">{formatTime(entry.timestamp)}</span>}
          </p>
          <div className="bg-brand-cream border border-[#e8d8d2] rounded-lg rounded-tl-sm px-3 py-2 text-sm text-brand-navy whitespace-pre-wrap">
            {entry.content}
          </div>
        </div>
      </div>
    );
  }

  if (role === 'assistant' || role === 'ai' || role === 'bot' || role === 'agent') {
    return (
      <div className="flex gap-3 max-w-[85%] ml-auto flex-row-reverse">
        <div className="w-7 h-7 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center shrink-0 mt-0.5">
          <Bot size={13} className="text-brand-pink" />
        </div>
        <div className="text-right">
          <p className="text-[10px] text-brand-muted mb-1">
            Assistant
            {entry.timestamp && <span className="ml-2">{formatTime(entry.timestamp)}</span>}
          </p>
          <div className="bg-brand-pink/5 border border-brand-pink/20 rounded-lg rounded-tr-sm px-3 py-2 text-sm text-brand-navy text-left whitespace-pre-wrap">
            {entry.content}
          </div>
        </div>
      </div>
    );
  }

  if (role === 'tool' || role === 'function' || role === 'tool_call' || role === 'tool_result') {
    return (
      <div className="mx-8">
        <div className="flex items-center gap-2 mb-1">
          <Wrench size={11} className="text-purple-400" />
          <span className="text-[10px] text-purple-400 font-mono">
            {entry.name || entry.tool_name || 'tool'}
          </span>
          {entry.timestamp && (
            <span className="text-[10px] text-brand-muted">{formatTime(entry.timestamp)}</span>
          )}
        </div>
        <div className="bg-purple-500/5 border border-purple-500/15 rounded-md px-3 py-2 text-xs font-mono text-brand-slate whitespace-pre-wrap overflow-x-auto">
          {entry.content ||
            (entry.tool_input
              ? JSON.stringify(entry.tool_input, null, 2)
              : '') +
            (entry.tool_output
              ? '\n\u2192 ' + (typeof entry.tool_output === 'string'
                ? entry.tool_output
                : JSON.stringify(entry.tool_output, null, 2))
              : '')}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-8">
      <p className="text-[10px] text-brand-muted mb-1">
        {role || 'system'}
        {entry.timestamp && <span className="ml-2">{formatTime(entry.timestamp)}</span>}
      </p>
      <div className="bg-white shadow-sm border border-brand-cream rounded-md px-3 py-2 text-xs text-brand-slate whitespace-pre-wrap">
        {entry.content || JSON.stringify(entry, null, 2)}
      </div>
    </div>
  );
}
