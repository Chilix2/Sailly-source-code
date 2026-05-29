/**
 * Quality Gate / Regression Dashboard
 * Shows regression test results, quality scores, and deploy gate status
 */
'use client';
import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Clock, TrendingUp, XCircle } from 'lucide-react';
export default function QualityGatePage() {
    const [metrics, setMetrics] = useState(null);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('all');
    useEffect(() => {
        fetchQualityGateData();
        // Poll for updates every 30 seconds
        const interval = setInterval(fetchQualityGateData, 30000);
        return () => clearInterval(interval);
    }, []);
    const fetchQualityGateData = async () => {
        try {
            // This would call your backend endpoint
            // For now, we'll simulate with placeholder data
            const mockMetrics = {
                overallScore: 87.5,
                passRate: 92,
                failCount: 2,
                lastRunTime: new Date().toISOString(),
                deployGateStatus: 'pass',
                scenariosRun: 25,
            };
            const mockResults = [
                {
                    scenario: 'Restaurant availability check',
                    status: 'pass',
                    score: 95,
                    details: 'Successfully checked 50 restaurants',
                    timestamp: new Date().toISOString(),
                },
                {
                    scenario: 'Reservation creation end-to-end',
                    status: 'pass',
                    score: 92,
                    details: 'Created and confirmed 100 reservations',
                    timestamp: new Date().toISOString(),
                },
                {
                    scenario: 'Multi-language support',
                    status: 'pass',
                    score: 88,
                    details: 'Tested German, English, Italian',
                    timestamp: new Date().toISOString(),
                },
                {
                    scenario: 'Payment handling with edge cases',
                    status: 'fail',
                    score: 65,
                    details: 'Failed on decimal rounding in 2/100 cases',
                    timestamp: new Date().toISOString(),
                },
                {
                    scenario: 'Escalation to human handover',
                    status: 'pass',
                    score: 90,
                    details: 'Correctly escalated 98/100 cases',
                    timestamp: new Date().toISOString(),
                },
                {
                    scenario: 'WhatsApp message formatting',
                    status: 'fail',
                    score: 70,
                    details: 'Unicode emoji handling failed in 1/20 tests',
                    timestamp: new Date().toISOString(),
                },
            ];
            setMetrics(mockMetrics);
            setResults(mockResults);
            setLoading(false);
        }
        catch (error) {
            console.error('Failed to fetch quality gate data:', error);
            setLoading(false);
        }
    };
    const filteredResults = results.filter((r) => {
        if (filter === 'all')
            return true;
        return r.status === filter;
    });
    const getStatusIcon = (status) => {
        switch (status) {
            case 'pass':
                return <CheckCircle className="w-5 h-5 text-green-500"/>;
            case 'fail':
                return <XCircle className="w-5 h-5 text-red-500"/>;
            case 'pending':
                return <Clock className="w-5 h-5 text-yellow-500"/>;
            default:
                return null;
        }
    };
    if (loading) {
        return (<div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-surface rounded-lg"></div>
          <div className="h-64 bg-surface rounded-lg"></div>
        </div>
      </div>);
    }
    return (<div className="space-y-8 p-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-text mb-2">Quality Gate Dashboard</h1>
        <p className="text-text-secondary">Regression tests and deployment gate status</p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-4 gap-6">
        {/* Overall Score */}
        <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-text-secondary text-sm font-medium">Overall Score</span>
            <TrendingUp className="w-4 h-4 text-border-glow"/>
          </div>
          <div className="text-4xl font-bold text-text">{metrics?.overallScore}%</div>
          <p className="text-text-secondary text-sm mt-2">Trend: ↑ 2.3% this week</p>
        </div>

        {/* Pass Rate */}
        <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-text-secondary text-sm font-medium">Pass Rate</span>
            <CheckCircle className="w-4 h-4 text-green-500"/>
          </div>
          <div className="text-4xl font-bold text-green-500">{metrics?.passRate}%</div>
          <p className="text-text-secondary text-sm mt-2">{metrics?.scenariosRun} scenarios run</p>
        </div>

        {/* Fail Count */}
        <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-text-secondary text-sm font-medium">Failures</span>
            <AlertCircle className="w-4 h-4 text-red-500"/>
          </div>
          <div className="text-4xl font-bold text-red-500">{metrics?.failCount}</div>
          <p className="text-text-secondary text-sm mt-2">Require action</p>
        </div>

        {/* Deploy Gate Status */}
        <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-text-secondary text-sm font-medium">Deploy Gate</span>
            {metrics?.deployGateStatus === 'pass' ? (<CheckCircle className="w-4 h-4 text-green-500"/>) : (<XCircle className="w-4 h-4 text-red-500"/>)}
          </div>
          <div className={`text-4xl font-bold ${metrics?.deployGateStatus === 'pass' ? 'text-green-500' : 'text-red-500'}`}>
            {metrics?.deployGateStatus === 'pass' ? 'PASS' : 'FAIL'}
          </div>
          <p className="text-text-secondary text-sm mt-2">Ready to deploy: {metrics?.deployGateStatus === 'pass' ? 'Yes' : 'No'}</p>
        </div>
      </div>

      {/* Test Results */}
      <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text">Regression Test Results</h2>
          <div className="flex gap-2">
            {['all', 'pass', 'fail'].map((f) => (<button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 rounded text-sm font-medium transition-colors ${filter === f
                ? 'bg-border-glow text-background'
                : 'bg-surface2 text-text-secondary hover:text-text'}`}>
                {f === 'all' ? 'All' : f === 'pass' ? 'Passing' : 'Failing'}
              </button>))}
          </div>
        </div>

        <div className="space-y-3">
          {filteredResults.map((result, idx) => (<div key={idx} className="flex items-start gap-4 p-4 rounded-lg bg-surface2 border border-border/50 hover:border-border-glow transition-colors">
              {/* Status Icon */}
              <div className="pt-1">{getStatusIcon(result.status)}</div>

              {/* Content */}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-text">{result.scenario}</h3>
                  <span className={`text-sm font-bold ${result.status === 'pass'
                ? 'text-green-500'
                : result.status === 'fail'
                    ? 'text-red-500'
                    : 'text-yellow-500'}`}>
                    {result.score}%
                  </span>
                </div>
                <p className="text-sm text-text-secondary mb-2">{result.details}</p>
                <p className="text-xs text-text-secondary/60">
                  {new Date(result.timestamp).toLocaleString()}
                </p>
              </div>

              {/* Score Bar */}
              <div className="w-24 pt-1">
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div className={`h-full transition-all ${result.score >= 90
                ? 'bg-green-500'
                : result.score >= 70
                    ? 'bg-yellow-500'
                    : 'bg-red-500'}`} style={{ width: `${result.score}%` }}></div>
                </div>
              </div>
            </div>))}
        </div>
      </div>

      {/* Learning Loop Report */}
      <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
        <h2 className="text-xl font-bold text-text mb-4">Learning Loop Report</h2>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-semibold text-text-secondary mb-3">Top Failure Categories</h3>
            <ul className="space-y-2">
              <li className="flex justify-between text-sm">
                <span className="text-text">Payment edge cases</span>
                <span className="text-red-500 font-semibold">8 failures</span>
              </li>
              <li className="flex justify-between text-sm">
                <span className="text-text">Unicode handling</span>
                <span className="text-red-500 font-semibold">3 failures</span>
              </li>
              <li className="flex justify-between text-sm">
                <span className="text-text">Timeout scenarios</span>
                <span className="text-yellow-500 font-semibold">2 warnings</span>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-secondary mb-3">Recommended Improvements</h3>
            <ul className="space-y-2 text-sm text-text">
              <li>• Add decimal precision handling to payment processor</li>
              <li>• Upgrade emoji regex pattern for WhatsApp</li>
              <li>• Increase ElevenLabs API timeout from 5s to 8s</li>
              <li>• Review Claude prompt for better multi-language support</li>
            </ul>
          </div>
        </div>
      </div>
    </div>);
}
