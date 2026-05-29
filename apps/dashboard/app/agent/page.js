'use client';
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Send, RotateCcw, GitBranch } from 'lucide-react';
const mockPromptVersions = [
    {
        id: 'v1.0',
        timestamp: new Date(Date.now() - 86400000),
        status: 'active',
        qualityScore: 89,
        description: 'Initial DOBOO persona - German only, formal',
    },
    {
        id: 'v0.9',
        timestamp: new Date(Date.now() - 172800000),
        status: 'archived',
        qualityScore: 84,
        description: 'Beta testing - casual tone attempt',
    },
    {
        id: 'v0.8',
        timestamp: new Date(Date.now() - 259200000),
        status: 'archived',
        qualityScore: 78,
        description: 'Early prototype',
    },
];
const mockSystemPrompt = `You are DOBOO, a professional AI assistant for a Korean restaurant. Your role is to help customers make reservations, answer menu questions, and process food orders.

## Instructions
1. Always respond in German
2. Be professional and helpful
3. When a customer wants a reservation, confirm date, time, party size, and name
4. For orders, describe menu items and confirm selections
5. If the customer asks for something outside your scope, offer to transfer to a human

## Restaurant Info
- Name: DOBOO Korean SoulFood
- Operating Hours: 10:00-23:00 daily
- Specialties: Korean cuisine, bibimbap, bulgogi, kimchi
- Max party size: 12 people
- Reservation required for 6+ people`;
export default function AgentConfigPage() {
    const [selectedVersion, setSelectedVersion] = useState(mockPromptVersions[0]);
    const [editMode, setEditMode] = useState(false);
    const [promptText, setPromptText] = useState(mockSystemPrompt);
    const [showABTest, setShowABTest] = useState(false);
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">
            Agent Config <span className="text-accent">[P1 TODO]</span>
          </h1>
          <p className="text-text-dim">System prompt editor, version history, A/B testing, push-to-ElevenLabs</p>
        </div>

        {/* Version history */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass p-6 rounded-lg mb-8">
          <h2 className="text-lg font-bold text-text mb-4 flex items-center gap-2">
            <GitBranch size={20} className="text-accent"/>
            Prompt Versions
          </h2>

          <div className="space-y-3">
            {mockPromptVersions.map((version) => (<motion.div key={version.id} onClick={() => {
                setSelectedVersion(version);
                setEditMode(false);
            }} whileHover={{ scale: 1.01 }} className={`glass-hover p-4 rounded-lg cursor-pointer transition-all ${selectedVersion.id === version.id ? 'border-accent ring-2 ring-accent/20' : ''}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-text">{version.id}</h3>
                    <p className="text-xs text-text-muted mt-1">{version.description}</p>
                    <p className="text-xs text-text-dim mt-1">{version.timestamp.toLocaleString()}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-xs text-text-muted mb-1">Quality Score</p>
                      <p className="text-lg font-bold text-accent">{version.qualityScore}%</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${version.status === 'active'
                ? 'bg-accent-3/20 text-accent-3'
                : 'bg-text-muted/20 text-text-muted'}`}>
                      {version.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </motion.div>))}
          </div>
        </motion.div>

        {/* Prompt editor */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass p-6 rounded-lg mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-text">System Prompt - {selectedVersion.id}</h2>
            <button onClick={() => setEditMode(!editMode)} className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors">
              {editMode ? '✓ Done' : '✎ Edit'}
            </button>
          </div>

          <textarea value={promptText} onChange={(e) => setPromptText(e.target.value)} disabled={!editMode} className="w-full h-80 bg-surface border border-border rounded-lg p-4 text-text font-mono text-sm focus:outline-none focus:border-accent disabled:opacity-75" placeholder="System prompt..."/>

          {editMode && (<div className="flex gap-3 mt-4">
              <button className="glass px-4 py-2 rounded-lg text-accent-3 text-sm hover:bg-white/10 transition-colors flex items-center gap-2">
                <Send size={16}/>
                Save as Draft
              </button>
              <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors flex items-center gap-2">
                <Send size={16}/>
                Push to ElevenLabs (Staging)
              </button>
              <button onClick={() => {
                setEditMode(false);
                setPromptText(mockSystemPrompt);
            }} className="glass px-4 py-2 rounded-lg text-text-muted text-sm hover:bg-white/10 transition-colors flex items-center gap-2">
                <RotateCcw size={16}/>
                Cancel
              </button>
            </div>)}
        </motion.div>

        {/* Deployment actions */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="grid grid-cols-2 gap-8 mb-8">
          <div className="glass p-6 rounded-lg">
            <h3 className="text-lg font-bold text-text mb-4">Deployment</h3>
            <div className="space-y-3">
              <button className="w-full glass-hover px-4 py-3 rounded-lg text-left text-text-dim text-sm hover:text-accent transition-colors">
                Deploy to Staging Environment
              </button>
              <button className="w-full glass-hover px-4 py-3 rounded-lg text-left text-text-dim text-sm hover:text-accent transition-colors">
                Rollback to v0.9
              </button>
              <button className="w-full glass-hover px-4 py-3 rounded-lg text-left text-text-dim text-sm hover:text-accent transition-colors">
                Deploy to Production
              </button>
            </div>
          </div>

          <div className="glass p-6 rounded-lg">
            <h3 className="text-lg font-bold text-text mb-4">A/B Testing</h3>
            <div className="space-y-3">
              <button onClick={() => setShowABTest(!showABTest)} className="w-full glass-hover px-4 py-3 rounded-lg text-left text-text-dim text-sm hover:text-accent transition-colors">
                Start A/B Test (v1.0 vs v0.9)
              </button>
              <button className="w-full glass-hover px-4 py-3 rounded-lg text-left text-text-dim text-sm hover:text-accent transition-colors opacity-50">
                View Active Test Results
              </button>
            </div>

            {showABTest && (<motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-3 bg-accent/10 border border-accent/30 rounded text-xs text-text-dim">
                <p className="mb-2 font-semibold text-text">Test Configuration</p>
                <p>A: v1.0 (50% traffic)</p>
                <p>B: v0.9 (50% traffic)</p>
                <p className="mt-2 text-text-muted">Status: <span className="text-accent-3">RUNNING</span></p>
                <p className="text-text-muted">Duration: <span className="text-accent-3">7 days</span></p>
              </motion.div>)}
          </div>
        </motion.div>

        {/* Configuration */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass p-6 rounded-lg">
          <h3 className="text-lg font-bold text-text mb-4">Voice & Model Configuration</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="text-sm text-text-muted mb-2 block">Voice ID</label>
              <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text focus:outline-none focus:border-accent">
                <option>alloy_v3 (German - Professional)</option>
                <option>echo_v2</option>
                <option>shimmer_v1</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted mb-2 block">LLM Model</label>
              <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text focus:outline-none focus:border-accent">
                <option>claude-haiku-4-5 (via proxy)</option>
                <option>claude-opus</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted mb-2 block">Language</label>
              <select className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text focus:outline-none focus:border-accent">
                <option>German (de-DE)</option>
                <option>English (en-US)</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-text-muted mb-2 block">Temperature (Creativity)</label>
              <input type="range" min="0" max="1" step="0.1" defaultValue="0.7" className="w-full"/>
              <p className="text-xs text-text-muted mt-1">0.7</p>
            </div>
          </div>
        </motion.div>

        {/* Note */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8 p-4 bg-accent-warn/10 border border-accent-warn/30 rounded-lg text-sm text-accent-warn">
          ⚠️ This is a <strong>mock prototype</strong> for P1 priority design. Features to implement:
          <ul className="mt-2 ml-4 space-y-1 text-xs">
            <li>• Connect to ElevenLabs agent API for real prompt updates</li>
            <li>• Implement version control in database</li>
            <li>• Create A/B test infrastructure with proper metrics collection</li>
            <li>• Hook into quality-gate regression testing</li>
          </ul>
        </motion.div>
      </motion.div>
    </div>);
}
