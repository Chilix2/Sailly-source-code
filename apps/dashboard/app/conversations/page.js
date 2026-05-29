'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Search, Download, AlertCircle, CheckCircle, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { fetchAPI } from '@/lib/api';
export default function ConversationsPage() {
    const [conversations, setConversations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isLive, setIsLive] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedConversation, setSelectedConversation] = useState(null);
    const [filterOutcome, setFilterOutcome] = useState(null);
    const [lastRefresh, setLastRefresh] = useState(null);
    const loadConversations = useCallback(async () => {
        setLoading(true);
        setError(null);
        const result = await fetchAPI('/api/dashboard/conversations?limit=50');
        if (result.success && result.data) {
            setConversations(result.data);
            setIsLive(true);
        }
        else {
            setError(result.error || 'Failed to load');
            setIsLive(false);
        }
        setLastRefresh(new Date());
        setLoading(false);
    }, []);
    useEffect(() => {
        loadConversations();
        const interval = setInterval(loadConversations, 30000);
        return () => clearInterval(interval);
    }, [loadConversations]);
    const outcomes = [...new Set(conversations.map((c) => c.outcome).filter(Boolean))];
    const filteredConversations = conversations.filter((conv) => {
        const matchesSearch = !searchTerm ||
            conv.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            conv.phoneNumber.includes(searchTerm) ||
            conv.status.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesFilter = !filterOutcome || conv.outcome === filterOutcome;
        return matchesSearch && matchesFilter;
    });
    const formatDuration = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
    };
    const formatTime = (ts) => {
        try {
            return new Date(ts).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
        }
        catch {
            return ts;
        }
    };
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text mb-2">
              Conversations <span className="text-accent">Browser</span>
            </h1>
            <p className="text-text-dim">
              {isLive ? (<span className="flex items-center gap-2">
                  <Wifi size={14} className="text-accent-3"/>
                  Live data &middot; {conversations.length} conversations
                  {lastRefresh && <span className="text-text-muted"> &middot; {formatTime(lastRefresh.toISOString())}</span>}
                </span>) : (<span className="flex items-center gap-2">
                  <WifiOff size={14} className="text-accent-warn"/>
                  {error ? `Backend unreachable: ${error}` : 'No data yet'}
                </span>)}
            </p>
          </div>
          <button onClick={loadConversations} disabled={loading} className="glass-hover px-4 py-2 rounded-lg text-sm text-accent flex items-center gap-2">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''}/>
            Refresh
          </button>
        </div>

        {/* Search and filters */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass p-6 rounded-lg mb-8">
          <div className="flex gap-4 mb-4">
            <div className="flex-1 relative">
              <Search size={18} className="absolute left-3 top-3 text-text-muted"/>
              <input type="text" placeholder="Search by conversation ID, phone, or status..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full pl-10 pr-4 py-2 bg-surface border border-border rounded-lg text-text placeholder-text-muted focus:outline-none focus:border-accent"/>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap">
            <button onClick={() => setFilterOutcome(null)} className={`px-4 py-2 rounded-lg text-sm transition-all ${filterOutcome === null
            ? 'bg-accent/20 border border-accent text-accent'
            : 'glass text-text-muted hover:text-accent'}`}>
              All ({conversations.length})
            </button>
            {outcomes.map((outcome) => (<button key={outcome} onClick={() => setFilterOutcome(outcome)} className={`px-4 py-2 rounded-lg text-sm transition-all ${filterOutcome === outcome
                ? 'bg-accent/20 border border-accent text-accent'
                : 'glass text-text-muted hover:text-accent'}`}>
                {outcome.replace(/_/g, ' ')} ({conversations.filter((c) => c.outcome === outcome).length})
              </button>))}
          </div>
        </motion.div>

        {/* Empty state */}
        {!loading && filteredConversations.length === 0 && (<div className="glass p-12 rounded-lg text-center">
            <AlertCircle size={48} className="mx-auto text-text-muted mb-4"/>
            <h3 className="text-lg font-semibold text-text mb-2">
              {conversations.length === 0 ? 'No conversations yet' : 'No matches'}
            </h3>
            <p className="text-text-dim">
              {conversations.length === 0
                ? 'Conversations will appear here as calls come in via the voice agent.'
                : 'Try adjusting your search or filter.'}
            </p>
          </div>)}

        {/* Conversation list */}
        <div className="space-y-4">
          {filteredConversations.map((conv, i) => (<motion.div key={conv.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: Math.min(i * 0.05, 0.5) }} onClick={() => setSelectedConversation(selectedConversation?.id === conv.id ? null : conv)} className="glass-hover p-6 rounded-lg cursor-pointer">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-text font-mono text-sm">{conv.id}</h3>
                    <div className={`px-2 py-1 rounded-full text-xs font-semibold flex items-center gap-1 ${conv.status === 'completed'
                ? 'bg-accent-3/20 text-accent-3'
                : conv.status === 'failed'
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-accent-warn/20 text-accent-warn'}`}>
                      {conv.status === 'completed' ? <CheckCircle size={12}/> : <AlertCircle size={12}/>}
                      {conv.status.toUpperCase()}
                    </div>
                    {conv.qualityScore !== null && (<span className={`text-xs font-mono ${conv.qualityScore >= 80 ? 'text-accent-3' : 'text-accent-warn'}`}>
                        Q: {conv.qualityScore}%
                      </span>)}
                  </div>
                  <div className="grid grid-cols-5 gap-4 text-sm text-text-dim">
                    <div>
                      <span className="text-text-muted">Phone: </span>
                      {conv.phoneNumber}
                    </div>
                    <div>
                      <span className="text-text-muted">Duration: </span>
                      {formatDuration(conv.duration)}
                    </div>
                    <div>
                      <span className="text-text-muted">Language: </span>
                      {conv.language.toUpperCase()}
                    </div>
                    <div>
                      <span className="text-text-muted">Events: </span>
                      {conv.events}
                    </div>
                    <div>
                      <span className="text-text-muted">Time: </span>
                      {formatTime(conv.startTime)}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>))}
        </div>

        {/* Selected conversation detail */}
        {selectedConversation && (<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-12 glass p-8 rounded-lg">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-text mb-4">
                Conversation: <span className="font-mono">{selectedConversation.id}</span>
              </h2>

              <div className="grid grid-cols-4 gap-4 mb-8">
                <div>
                  <p className="text-xs text-text-muted mb-1">Status</p>
                  <p className="text-2xl font-bold text-accent">{selectedConversation.status}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Duration</p>
                  <p className="text-2xl font-bold text-accent">{formatDuration(selectedConversation.duration)}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Phone</p>
                  <p className="text-2xl font-bold text-accent">{selectedConversation.phoneNumber}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Quality</p>
                  <p className="text-2xl font-bold text-accent-3">
                    {selectedConversation.qualityScore !== null ? `${selectedConversation.qualityScore}%` : 'N/A'}
                  </p>
                </div>
              </div>
            </div>

            {/* Transcript events */}
            {selectedConversation.transcript && selectedConversation.transcript.length > 0 && (<div>
                <h3 className="font-semibold text-text mb-4">Transcript &amp; Events</h3>
                <div className="bg-surface border border-border rounded-lg p-4 space-y-3 font-mono text-sm">
                  {selectedConversation.transcript.map((entry, idx) => (<div key={idx} className="flex gap-4">
                      <span className="font-semibold min-w-fit text-accent">
                        {entry.type || 'event'}:
                      </span>
                      <div className="flex-1">
                        <pre className="whitespace-pre-wrap text-text-dim">
                          {typeof entry === 'string' ? entry : JSON.stringify(entry, null, 2)}
                        </pre>
                      </div>
                    </div>))}
                </div>
              </div>)}

            {/* Actions */}
            <div className="flex gap-4 mt-8">
              <button className="glass-hover px-4 py-2 rounded-lg text-sm text-accent flex items-center gap-2">
                <Download size={16}/>
                Export JSON
              </button>
            </div>
          </motion.div>)}
      </motion.div>
    </div>);
}
