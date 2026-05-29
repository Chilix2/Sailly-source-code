'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, TrendingUp, Zap } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
const mockRegressionRuns = [
    {
        id: 'run-2026-03-12-14',
        timestamp: '2026-03-12 14:32 UTC',
        status: 'pass',
        totalScenarios: 24,
        passed: 23,
        failed: 1,
        flaky: 0,
        deployGate: 'approved',
        scenarioDetails: [
            { id: 's1', name: 'Basic reservation flow', status: 'pass', score: 98, latency: 245 },
            { id: 's2', name: 'Multi-call upsell', status: 'pass', score: 95, latency: 312 },
            { id: 's3', name: 'Menu inquiry + order', status: 'pass', score: 92, latency: 289 },
            { id: 's4', name: 'Operating hours check', status: 'pass', score: 94, latency: 156 },
            { id: 's5', name: 'Callback handling', status: 'fail', score: 67, latency: 401 },
            { id: 's6', name: 'Special requests', status: 'pass', score: 91, latency: 223 },
        ],
    },
    {
        id: 'run-2026-03-12-08',
        timestamp: '2026-03-12 08:15 UTC',
        status: 'pass',
        totalScenarios: 24,
        passed: 24,
        failed: 0,
        flaky: 0,
        deployGate: 'approved',
        scenarioDetails: [
            { id: 's1', name: 'Basic reservation flow', status: 'pass', score: 97, latency: 251 },
            { id: 's2', name: 'Multi-call upsell', status: 'pass', score: 94, latency: 318 },
            { id: 's3', name: 'Menu inquiry + order', status: 'pass', score: 93, latency: 291 },
        ],
    },
];
const mockQualityTrends = [
    { date: 'Mar 08', overallScore: 91, containmentRate: 72, taskCompletion: 84, ttfb: 412 },
    { date: 'Mar 09', overallScore: 92, containmentRate: 73, taskCompletion: 85, ttfb: 408 },
    { date: 'Mar 10', overallScore: 93, containmentRate: 74, taskCompletion: 86, ttfb: 401 },
    { date: 'Mar 11', overallScore: 94, containmentRate: 76, taskCompletion: 88, ttfb: 395 },
    { date: 'Mar 12', overallScore: 94, containmentRate: 75, taskCompletion: 87, ttfb: 398 },
];
const mockLearningLoopReport = {
    reportDate: '2026-03-12T06:00:00Z',
    status: 'completed',
    improvementsSuggested: 12,
    scenariosGenerated: 89,
    topFailureCategories: [
        { category: 'Intent misclassification', count: 14, severity: 'high' },
        { category: 'Timeout on tool calls', count: 8, severity: 'medium' },
        { category: 'TTS latency spike', count: 5, severity: 'medium' },
        { category: 'False escalations', count: 3, severity: 'low' },
    ],
    promptImprovementPlan: 'Add guardrails for ambiguous intents, optimize tool call retry logic',
    estimatedScoreImprovement: 2.3,
};
export default function QualityGatePage() {
    const [selectedRun, setSelectedRun] = useState(mockRegressionRuns[0]);
    const [expandedScenario, setExpandedScenario] = useState(null);
    const latestRun = mockRegressionRuns[0];
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-4xl font-bold text-text mb-2">Quality Gate Dashboard</h1>
        <p className="text-text-muted mb-8">Regression test results, quality score trends, and AI learning loop reports</p>
      </motion.div>

      {/* Deploy Gate Status */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }} className="glass p-8 rounded-lg mb-8 border border-border">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-text">Deploy Gate Status</h2>
            <p className="text-text-muted text-sm mt-1">Latest regression run: {latestRun.timestamp}</p>
          </div>
          <div className="flex items-center gap-3">
            {latestRun.deployGate === 'approved' ? (<>
                <CheckCircle size={32} className="text-green-500"/>
                <div>
                  <p className="text-lg font-semibold text-green-400">Gate Approved</p>
                  <p className="text-sm text-text-muted">Ready to deploy</p>
                </div>
              </>) : (<>
                <XCircle size={32} className="text-red-500"/>
                <div>
                  <p className="text-lg font-semibold text-red-400">Gate Blocked</p>
                  <p className="text-sm text-text-muted">Regression failed</p>
                </div>
              </>)}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4">
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Total Scenarios</p>
            <p className="text-3xl font-bold text-accent mt-2">{latestRun.totalScenarios}</p>
          </div>
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Passed</p>
            <p className="text-3xl font-bold text-green-400 mt-2">{latestRun.passed}</p>
            <p className="text-xs text-text-muted mt-1">{((latestRun.passed / latestRun.totalScenarios) * 100).toFixed(0)}% pass rate</p>
          </div>
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Failed</p>
            <p className={`text-3xl font-bold mt-2 ${latestRun.failed > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {latestRun.failed}
            </p>
          </div>
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Flaky</p>
            <p className={`text-3xl font-bold mt-2 ${latestRun.flaky > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
              {latestRun.flaky}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Quality Score Trends */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }} className="glass p-8 rounded-lg mb-8 border border-border">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp size={20} className="text-accent"/>
          <h2 className="text-xl font-semibold text-text">Quality Score Trends (7 days)</h2>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={mockQualityTrends}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a3050"/>
            <XAxis dataKey="date" stroke="#8b95a5"/>
            <YAxis stroke="#8b95a5"/>
            <Tooltip contentStyle={{
            backgroundColor: '#0e1e35',
            border: '1px solid #1a3050',
            borderRadius: '8px',
        }} labelStyle={{ color: '#e0e7ff' }}/>
            <Legend />
            <Line type="monotone" dataKey="overallScore" stroke="#00d4ff" name="Overall Score" dot={{ fill: '#00d4ff', r: 4 }} strokeWidth={2}/>
            <Line type="monotone" dataKey="containmentRate" stroke="#10b981" name="Containment Rate" dot={{ fill: '#10b981', r: 4 }} strokeWidth={2}/>
            <Line type="monotone" dataKey="taskCompletion" stroke="#8b5cf6" name="Task Completion" dot={{ fill: '#8b5cf6', r: 4 }} strokeWidth={2}/>
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Regression Scenarios */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }} className="glass p-8 rounded-lg mb-8 border border-border">
        <h2 className="text-xl font-semibold text-text mb-6">Regression Scenarios</h2>
        <div className="space-y-3">
          {selectedRun.scenarioDetails.map((scenario) => (<motion.div key={scenario.id} whileHover={{ scale: 1.02 }} onClick={() => setExpandedScenario(expandedScenario === scenario.id ? null : scenario.id)} className="bg-surface p-4 rounded-lg border border-border cursor-pointer transition-all hover:border-accent/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  {scenario.status === 'pass' && <CheckCircle size={20} className="text-green-400"/>}
                  {scenario.status === 'fail' && <XCircle size={20} className="text-red-400"/>}
                  {scenario.status === 'flaky' && <AlertCircle size={20} className="text-yellow-400"/>}
                  <div className="flex-1">
                    <p className="text-text font-medium">{scenario.name}</p>
                    <p className="text-text-muted text-xs">ID: {scenario.id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-text font-semibold">{scenario.score}%</p>
                    <p className="text-text-muted text-xs">Score</p>
                  </div>
                  <div className="text-right">
                    <p className="text-text font-semibold">{scenario.latency}ms</p>
                    <p className="text-text-muted text-xs">Latency</p>
                  </div>
                </div>
              </div>
              {expandedScenario === scenario.id && (<motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mt-4 pt-4 border-t border-border/50">
                  <p className="text-text-muted text-sm">
                    Scenario details: {scenario.name} executed with {scenario.score}% accuracy. Latency measured at {scenario.latency}ms on the critical path.
                  </p>
                </motion.div>)}
            </motion.div>))}
        </div>
      </motion.div>

      {/* Learning Loop Report */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.4 }} className="glass p-8 rounded-lg border border-border">
        <div className="flex items-center gap-2 mb-6">
          <Zap size={20} className="text-accent"/>
          <h2 className="text-xl font-semibold text-text">Learning Loop Report</h2>
          <span className="text-xs px-2 py-1 bg-accent/10 text-accent rounded-full border border-accent/30 ml-auto">
            Last run: {new Date(mockLearningLoopReport.reportDate).toLocaleString()}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Improvements Suggested</p>
            <p className="text-3xl font-bold text-accent mt-2">{mockLearningLoopReport.improvementsSuggested}</p>
          </div>
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Scenarios Generated</p>
            <p className="text-3xl font-bold text-accent-3 mt-2">{mockLearningLoopReport.scenariosGenerated}</p>
          </div>
          <div className="bg-surface p-4 rounded-lg border border-border">
            <p className="text-text-muted text-sm font-medium">Est. Score Improvement</p>
            <p className="text-3xl font-bold text-green-400 mt-2">+{mockLearningLoopReport.estimatedScoreImprovement}%</p>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-lg font-semibold text-text mb-3">Top Failure Categories</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={mockLearningLoopReport.topFailureCategories}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3050"/>
              <XAxis dataKey="category" stroke="#8b95a5" angle={-45} textAnchor="end" height={100}/>
              <YAxis stroke="#8b95a5"/>
              <Tooltip contentStyle={{
            backgroundColor: '#0e1e35',
            border: '1px solid #1a3050',
            borderRadius: '8px',
        }} labelStyle={{ color: '#e0e7ff' }}/>
              <Bar dataKey="count" fill="#00d4ff" name="Failure Count"/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-surface/50 p-4 rounded-lg border border-border">
          <p className="text-text-muted text-sm font-medium mb-2">Recommended Improvements</p>
          <p className="text-text">{mockLearningLoopReport.promptImprovementPlan}</p>
        </div>
      </motion.div>

      {/* Mock Prototype Note */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.5 }} className="mt-8 p-4 bg-accent-warn/10 border border-accent-warn/30 rounded-lg text-sm text-accent-warn">
        ⚠️ This is a <strong>mock prototype</strong> for P1 priority design. To integrate with real data:
        <ul className="list-disc list-inside mt-2 text-xs">
          <li>Connect to Fastify backend <code className="text-accent-warn/70 bg-black/20 px-1 rounded">GET /regression/latest</code> endpoint</li>
          <li>Poll learning loop reports from <code className="text-accent-warn/70 bg-black/20 px-1 rounded">.state/reports/</code> or API endpoint</li>
          <li>Wire up Server-Sent Events (SSE) for real-time regression run notifications</li>
          <li>Display failure details from regression gate logs</li>
        </ul>
      </motion.div>
    </div>);
}
