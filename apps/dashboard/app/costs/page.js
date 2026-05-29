'use client';
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { TrendingDown, AlertTriangle, Download } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
const mockCostData = [
    { date: 'Mar 8', twilio: 45.2, elevenlabs: 82.3, claude: 34.1, total: 161.6 },
    { date: 'Mar 9', twilio: 52.1, elevenlabs: 95.2, claude: 42.3, total: 189.6 },
    { date: 'Mar 10', twilio: 48.9, elevenlabs: 88.7, claude: 38.9, total: 176.5 },
    { date: 'Mar 11', twilio: 61.3, elevenlabs: 112.4, claude: 51.2, total: 224.9 },
    { date: 'Mar 12', twilio: 55.7, elevenlabs: 98.1, claude: 44.8, total: 198.6 },
];
const mockPerCallCosts = [
    { callId: 'conv_abc123', restaurant: 'DOBOO', callDuration: 145, twilio: 0.3, elevenlabs: 0.45, claude: 0.18, sms: 0.01, total: 0.97 },
    { callId: 'conv_def456', restaurant: 'DOBOO', callDuration: 89, twilio: 0.22, elevenlabs: 0.32, claude: 0.12, sms: 0.01, total: 0.67 },
    { callId: 'conv_ghi789', restaurant: 'DOBOO', callDuration: 156, twilio: 0.35, elevenlabs: 0.58, claude: 0.24, sms: 0.01, total: 1.18 },
    { callId: 'conv_jkl012', restaurant: 'DOBOO', callDuration: 234, twilio: 0.51, elevenlabs: 0.87, claude: 0.38, sms: 0.01, total: 1.77 },
];
const mockRestaurantCosts = [
    { restaurant: 'DOBOO', calls: 1243, avgCostPerCall: 0.82, dailyAvg: 185.2, estimatedMonthly: 5556 },
    { restaurant: 'Restaurant B', calls: 856, avgCostPerCall: 0.79, dailyAvg: 142.8, estimatedMonthly: 4284 },
    { restaurant: 'Restaurant C', calls: 623, avgCostPerCall: 0.85, dailyAvg: 118.9, estimatedMonthly: 3567 },
];
export default function CostsPage() {
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const totalDaily = mockCostData[mockCostData.length - 1].total;
    const totalWeekly = mockCostData.reduce((sum, d) => sum + d.total, 0);
    const avgDaily = (totalWeekly / mockCostData.length).toFixed(2);
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">
            Cost Dashboard <span className="text-accent">[P1 Partial]</span>
          </h1>
          <p className="text-text-dim">Per-call cost aggregation, daily trends, cost per restaurant</p>
        </div>

        {/* Key metrics */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-4 gap-4 mb-8">
          <div className="glass p-6 rounded-lg">
            <p className="text-xs text-text-muted mb-2">Today&apos;s Spend</p>
            <p className="text-3xl font-bold text-accent">${totalDaily.toFixed(2)}</p>
            <p className="text-xs text-accent-3 mt-2 flex items-center gap-1">
              <TrendingDown size={12}/> -8.4% vs yesterday
            </p>
          </div>

          <div className="glass p-6 rounded-lg">
            <p className="text-xs text-text-muted mb-2">7-Day Total</p>
            <p className="text-3xl font-bold text-accent">${totalWeekly.toFixed(2)}</p>
            <p className="text-xs text-accent-2 mt-2">Avg: ${avgDaily}/day</p>
          </div>

          <div className="glass p-6 rounded-lg">
            <p className="text-xs text-text-muted mb-2">Budget Status</p>
            <p className="text-3xl font-bold text-accent-3">$5,850 / $6,000</p>
            <p className="text-xs text-text-muted mt-2">97.5% of monthly budget</p>
          </div>

          <div className="glass p-6 rounded-lg">
            <p className="text-xs text-text-muted mb-2">Avg Cost/Call</p>
            <p className="text-3xl font-bold text-accent">$0.81</p>
            <p className="text-xs text-accent-warn mt-2 flex items-center gap-1">
              <AlertTriangle size={12}/> Monitor closely
            </p>
          </div>
        </motion.div>

        {/* Daily cost trend */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass p-6 rounded-lg mb-8">
          <h2 className="text-lg font-bold text-text mb-4">Daily Cost Breakdown (7 days)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={mockCostData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)"/>
              <XAxis dataKey="date" stroke="rgba(255,255,255,0.5)"/>
              <YAxis stroke="rgba(255,255,255,0.5)"/>
              <Tooltip contentStyle={{
            backgroundColor: 'rgba(10, 10, 20, 0.9)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
        }} cursor={{ stroke: 'rgba(0, 212, 255, 0.2)' }}/>
              <Legend />
              <Line type="monotone" dataKey="twilio" stroke="#3b82f6" strokeWidth={2}/>
              <Line type="monotone" dataKey="elevenlabs" stroke="#a855f7" strokeWidth={2}/>
              <Line type="monotone" dataKey="claude" stroke="#ec4899" strokeWidth={2}/>
              <Line type="monotone" dataKey="total" stroke="#00d4ff" strokeWidth={2} dot={{ fill: '#00d4ff', r: 4 }}/>
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Cost per provider breakdown */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="grid grid-cols-2 gap-8 mb-8">
          <div className="glass p-6 rounded-lg">
            <h3 className="text-lg font-bold text-text mb-4">Provider Breakdown (Last 24h)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={mockCostData.slice(-1)}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)"/>
                <XAxis dataKey="date" stroke="rgba(255,255,255,0.5)"/>
                <YAxis stroke="rgba(255,255,255,0.5)"/>
                <Tooltip contentStyle={{
            backgroundColor: 'rgba(10, 10, 20, 0.9)',
            border: '1px solid rgba(255,255,255,0.1)',
        }}/>
                <Legend />
                <Bar dataKey="twilio" fill="#3b82f6"/>
                <Bar dataKey="elevenlabs" fill="#a855f7"/>
                <Bar dataKey="claude" fill="#ec4899"/>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="glass p-6 rounded-lg">
            <h3 className="text-lg font-bold text-text mb-4">Cost per Restaurant</h3>
            <div className="space-y-3">
              {mockRestaurantCosts.map((rest) => (<div key={rest.restaurant} onClick={() => setSelectedRestaurant(selectedRestaurant === rest.restaurant ? null : rest.restaurant)} className="glass-hover p-3 rounded-lg cursor-pointer">
                  <div className="flex justify-between items-center mb-1">
                    <p className="font-semibold text-text text-sm">{rest.restaurant}</p>
                    <p className="text-accent font-mono text-sm">${rest.avgCostPerCall}/call</p>
                  </div>
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>{rest.calls} calls</span>
                    <span>${rest.dailyAvg.toFixed(2)}/day</span>
                    <span>${rest.estimatedMonthly}/month est.</span>
                  </div>
                </div>))}
            </div>
          </div>
        </motion.div>

        {/* Per-call cost table */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="glass p-6 rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-text">Recent Calls - Cost Breakdown</h3>
            <button className="text-accent hover:text-accent-2 transition-colors flex items-center gap-2 text-sm">
              <Download size={16}/>
              Export
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-text-muted font-semibold">Call ID</th>
                  <th className="text-left py-3 px-4 text-text-muted font-semibold">Restaurant</th>
                  <th className="text-center py-3 px-4 text-text-muted font-semibold">Duration</th>
                  <th className="text-right py-3 px-4 text-text-muted font-semibold">Twilio</th>
                  <th className="text-right py-3 px-4 text-text-muted font-semibold">ElevenLabs</th>
                  <th className="text-right py-3 px-4 text-text-muted font-semibold">Claude</th>
                  <th className="text-right py-3 px-4 text-text-muted font-semibold">SMS</th>
                  <th className="text-right py-3 px-4 text-accent font-semibold">Total</th>
                </tr>
              </thead>
              <tbody>
                {mockPerCallCosts.map((call) => (<tr key={call.callId} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 text-text font-mono">{call.callId}</td>
                    <td className="py-3 px-4 text-text-dim">{call.restaurant}</td>
                    <td className="py-3 px-4 text-center text-text-dim">{call.callDuration}s</td>
                    <td className="py-3 px-4 text-right text-text-dim">${call.twilio.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right text-text-dim">${call.elevenlabs.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right text-text-dim">${call.claude.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right text-text-dim">${call.sms.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right text-accent font-semibold">${call.total.toFixed(2)}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Note */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-8 p-4 bg-accent-warn/10 border border-accent-warn/30 rounded-lg text-sm text-accent-warn">
          ⚠️ This is a <strong>mock prototype</strong> for P1 priority design. To populate with real data:
          <ul className="mt-2 ml-4 space-y-1 text-xs">
            <li>• Connect to Twilio Usage Records API for call minutes</li>
            <li>• Query ElevenLabs character usage via /v1/user/subscription endpoint</li>
            <li>• Log Claude tokens from proxy response headers</li>
            <li>• Correlate by CallSid + timestamp to calculate per-call costs</li>
            <li>• Store in call_pipeline_events table for historical tracking</li>
          </ul>
        </motion.div>
      </motion.div>
    </div>);
}
