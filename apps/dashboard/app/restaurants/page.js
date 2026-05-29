'use client';
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
const mockRestaurants = [
    {
        id: 'doboo_1',
        name: 'DOBOO Korean SoulFood',
        status: 'active',
        phone: '+491234567890',
        operatingHours: '10:00 - 23:00',
        language: 'German',
        agentStatus: 'online',
        stats: {
            callsToday: 47,
            reservationsToday: 12,
            ordersToday: 8,
            qualityScore: 89,
            averageHandleTime: 145,
        },
        monthlyStats: {
            totalCalls: 1243,
            reservations: 412,
            orders: 156,
            revenue: 8240,
            churn: 2.1,
        },
    },
    {
        id: 'rest_2',
        name: 'Restaurant B',
        status: 'active',
        phone: '+491234567891',
        operatingHours: '11:00 - 22:00',
        language: 'German',
        agentStatus: 'online',
        stats: {
            callsToday: 34,
            reservationsToday: 9,
            ordersToday: 5,
            qualityScore: 85,
            averageHandleTime: 156,
        },
        monthlyStats: {
            totalCalls: 856,
            reservations: 287,
            orders: 92,
            revenue: 5640,
            churn: 3.2,
        },
    },
    {
        id: 'rest_3',
        name: 'Restaurant C',
        status: 'onboarding',
        phone: '+491234567892',
        operatingHours: 'Not set',
        language: 'German',
        agentStatus: 'offline',
        stats: {
            callsToday: 0,
            reservationsToday: 0,
            ordersToday: 0,
            qualityScore: 0,
            averageHandleTime: 0,
        },
        monthlyStats: {
            totalCalls: 23,
            reservations: 8,
            orders: 2,
            revenue: 450,
            churn: 25.0,
        },
    },
];
const mockAnalytics = [
    { date: 'Mon', calls: 180, reservations: 54, orders: 22 },
    { date: 'Tue', calls: 195, reservations: 62, orders: 28 },
    { date: 'Wed', calls: 172, reservations: 51, orders: 19 },
    { date: 'Thu', calls: 210, reservations: 68, orders: 31 },
    { date: 'Fri', calls: 245, reservations: 82, orders: 41 },
    { date: 'Sat', calls: 298, reservations: 105, orders: 52 },
    { date: 'Sun', calls: 198, reservations: 58, orders: 24 },
];
export default function RestaurantsPage() {
    const [selectedRestaurant, setSelectedRestaurant] = useState(mockRestaurants[0]);
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">
            Restaurant Management <span className="text-accent">[P1 Partial]</span>
          </h1>
          <p className="text-text-dim">Multi-restaurant config, per-restaurant analytics, menu management</p>
        </div>

        {/* Restaurant list */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
          {mockRestaurants.map((rest) => (<motion.div key={rest.id} onClick={() => setSelectedRestaurant(rest)} whileHover={{ scale: 1.02 }} className={`glass-hover p-5 rounded-lg cursor-pointer transition-all ${selectedRestaurant?.id === rest.id
                ? 'border-accent ring-2 ring-accent/20'
                : ''}`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-text">{rest.name}</h3>
                  <p className="text-xs text-text-muted mt-1">{rest.phone}</p>
                </div>
                <div className={`w-3 h-3 rounded-full ${rest.agentStatus === 'online' ? 'bg-accent-3 animate-pulse-gentle' : 'bg-text-muted'}`}/>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className={`px-2 py-1 rounded-full font-semibold ${rest.status === 'active'
                ? 'bg-accent-3/20 text-accent-3'
                : 'bg-accent-warn/20 text-accent-warn'}`}>
                  {rest.status.toUpperCase()}
                </span>
                <span className="text-text-muted">{rest.stats.callsToday} calls today</span>
              </div>

              {rest.stats.callsToday > 0 && (<div className="mt-3 pt-3 border-t border-border text-xs text-text-dim">
                  <p>Quality: <span className="text-accent-3">{rest.stats.qualityScore}%</span></p>
                  <p>Reservations: <span className="text-accent">{rest.stats.reservationsToday}</span></p>
                </div>)}
            </motion.div>))}
        </motion.div>

        {/* Restaurant detail */}
        {selectedRestaurant && (<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
            {/* Detail header */}
            <div className="glass p-6 rounded-lg">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-text mb-2">{selectedRestaurant.name}</h2>
                  <div className="flex gap-6 text-sm text-text-muted">
                    <span>📞 {selectedRestaurant.phone}</span>
                    <span>🕐 {selectedRestaurant.operatingHours}</span>
                    <span>🌍 {selectedRestaurant.language}</span>
                  </div>
                </div>
                <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors flex items-center gap-2">
                  <Settings size={16}/>
                  Configure
                </button>
              </div>

              {/* Today's stats */}
              <div className="grid grid-cols-5 gap-4">
                <div>
                  <p className="text-xs text-text-muted mb-1">Calls Today</p>
                  <p className="text-2xl font-bold text-accent">{selectedRestaurant.stats.callsToday}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Reservations</p>
                  <p className="text-2xl font-bold text-accent-3">{selectedRestaurant.stats.reservationsToday}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Orders</p>
                  <p className="text-2xl font-bold text-accent-2">{selectedRestaurant.stats.ordersToday}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Quality Score</p>
                  <p className={`text-2xl font-bold ${selectedRestaurant.stats.qualityScore >= 85 ? 'text-accent-3' : 'text-accent-warn'}`}>
                    {selectedRestaurant.stats.qualityScore}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-1">Avg Handle Time</p>
                  <p className="text-2xl font-bold text-accent-2">{selectedRestaurant.stats.averageHandleTime}s</p>
                </div>
              </div>
            </div>

            {/* Weekly analytics */}
            <div className="glass p-6 rounded-lg">
              <h3 className="text-lg font-bold text-text mb-4">Weekly Performance</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mockAnalytics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)"/>
                  <XAxis dataKey="date" stroke="rgba(255,255,255,0.5)"/>
                  <YAxis stroke="rgba(255,255,255,0.5)"/>
                  <Tooltip contentStyle={{
                backgroundColor: 'rgba(10, 10, 20, 0.9)',
                border: '1px solid rgba(255,255,255,0.1)',
            }}/>
                  <Legend />
                  <Bar dataKey="calls" fill="#00d4ff"/>
                  <Bar dataKey="reservations" fill="#10b981"/>
                  <Bar dataKey="orders" fill="#a855f7"/>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Monthly metrics */}
            <div className="glass p-6 rounded-lg">
              <h3 className="text-lg font-bold text-text mb-4">Monthly Metrics</h3>
              <div className="grid grid-cols-5 gap-4">
                <div>
                  <p className="text-xs text-text-muted mb-2">Total Calls</p>
                  <p className="text-2xl font-bold text-accent">{selectedRestaurant.monthlyStats.totalCalls}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-2">Reservations</p>
                  <p className="text-2xl font-bold text-accent-3">{selectedRestaurant.monthlyStats.reservations}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-2">Orders</p>
                  <p className="text-2xl font-bold text-accent-2">{selectedRestaurant.monthlyStats.orders}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-2">Revenue</p>
                  <p className="text-2xl font-bold text-accent">${selectedRestaurant.monthlyStats.revenue}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted mb-2">Churn Rate</p>
                  <p className={`text-2xl font-bold ${selectedRestaurant.monthlyStats.churn < 3 ? 'text-accent-3' : 'text-accent-warn'}`}>
                    {selectedRestaurant.monthlyStats.churn}%
                  </p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="glass p-6 rounded-lg">
              <h3 className="text-lg font-bold text-text mb-4">Management Actions</h3>
              <div className="flex gap-3 flex-wrap">
                <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors">
                  Edit Configuration
                </button>
                <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors">
                  Manage Menu
                </button>
                <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors">
                  Update Agent
                </button>
                <button className="glass px-4 py-2 rounded-lg text-accent text-sm hover:bg-white/10 transition-colors">
                  View Call History
                </button>
              </div>
            </div>
          </motion.div>)}

        {/* Note */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-8 p-4 bg-accent-warn/10 border border-accent-warn/30 rounded-lg text-sm text-accent-warn">
          ⚠️ This is a <strong>mock prototype</strong> for P1 priority design. Features to implement:
          <ul className="mt-2 ml-4 space-y-1 text-xs">
            <li>• Menu management CRUD interface (currently scripts/seed-doboo-menu-data.ts)</li>
            <li>• Agent persona editor (currently scripts/configure-sailly-via-api.ts)</li>
            <li>• Operating hours configuration</li>
            <li>• Onboarding wizard with CSV import</li>
          </ul>
        </motion.div>
      </motion.div>
    </div>);
}
