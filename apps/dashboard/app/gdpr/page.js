/**
 * GDPR / Compliance Dashboard
 * Data subject requests, retention status, PII audit, DPA compliance
 */
'use client';
import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, FileText, Lock, Shield, Trash2, User } from 'lucide-react';
export default function GDPRCompliancePage() {
    const [metrics, setMetrics] = useState(null);
    const [requests, setRequests] = useState([]);
    const [retentionStatus, setRetentionStatus] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    useEffect(() => {
        fetchComplianceData();
    }, []);
    const fetchComplianceData = async () => {
        try {
            // Mock data - would be replaced with actual API calls
            const mockMetrics = {
                dpaSignedDate: '2025-09-15',
                lastAuditDate: '2026-02-01',
                gdprCompliance: 94,
                dPIAssessmentStatus: 'completed',
                consentTrackingEnabled: true,
                piiRedactionActive: true,
                pendingRequestsCount: 3,
                completedRequestsThisMonth: 12,
            };
            const mockRequests = [
                {
                    id: 'DSR-20260312-001',
                    type: 'access',
                    status: 'in_progress',
                    requestedBy: 'contact@restaurant1.de',
                    submittedAt: '2026-03-10',
                    dueAt: '2026-04-09',
                    dataItems: 847,
                },
                {
                    id: 'DSR-20260311-002',
                    type: 'deletion',
                    status: 'pending',
                    requestedBy: 'customer@example.de',
                    submittedAt: '2026-03-11',
                    dueAt: '2026-04-10',
                    dataItems: 23,
                },
                {
                    id: 'DSR-20260308-003',
                    type: 'export',
                    status: 'completed',
                    requestedBy: 'admin@restaurant2.de',
                    submittedAt: '2026-03-01',
                    dueAt: '2026-03-31',
                    dataItems: 1250,
                },
            ];
            const mockRetention = [
                {
                    dataType: 'Call Transcripts',
                    totalRecords: 45230,
                    retainedRecords: 38420,
                    purgedRecords: 6810,
                    nextPurgeDate: '2026-06-12',
                    policy: '90 days (per GDPR)',
                },
                {
                    dataType: 'Audio Recordings',
                    totalRecords: 45230,
                    retainedRecords: 0,
                    purgedRecords: 45230,
                    nextPurgeDate: 'N/A',
                    policy: 'Deleted immediately',
                },
                {
                    dataType: 'Login Attempts',
                    totalRecords: 12847,
                    retainedRecords: 11230,
                    purgedRecords: 1617,
                    nextPurgeDate: '2026-05-15',
                    policy: '90 days (audit trail)',
                },
                {
                    dataType: 'Anonymized Metrics',
                    totalRecords: 1230450,
                    retainedRecords: 1230450,
                    purgedRecords: 0,
                    nextPurgeDate: '2027-03-12',
                    policy: '1 year (per GDPR)',
                },
            ];
            setMetrics(mockMetrics);
            setRequests(mockRequests);
            setRetentionStatus(mockRetention);
            setLoading(false);
        }
        catch (error) {
            console.error('Failed to fetch compliance data:', error);
            setLoading(false);
        }
    };
    const getStatusColor = (status) => {
        switch (status) {
            case 'completed':
            case 'signed':
                return 'text-green-500';
            case 'in_progress':
                return 'text-yellow-500';
            case 'pending':
                return 'text-orange-500';
            case 'denied':
            case 'overdue':
                return 'text-red-500';
            default:
                return 'text-text';
        }
    };
    const getRequestTypeIcon = (type) => {
        switch (type) {
            case 'access':
                return <User className="w-4 h-4"/>;
            case 'deletion':
                return <Trash2 className="w-4 h-4"/>;
            case 'export':
                return <FileText className="w-4 h-4"/>;
            case 'rectification':
                return <Shield className="w-4 h-4"/>;
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
        <h1 className="text-3xl font-bold text-text mb-2">GDPR & Compliance Dashboard</h1>
        <p className="text-text-secondary">Data protection, retention policies, and regulatory compliance</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border">
        {['overview', 'requests', 'retention', 'audit'].map((tab) => (<button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-3 font-medium text-sm transition-colors ${activeTab === tab
                ? 'text-text border-b-2 border-border-glow'
                : 'text-text-secondary hover:text-text'}`}>
            {tab === 'overview'
                ? 'Overview'
                : tab === 'requests'
                    ? 'Data Requests'
                    : tab === 'retention'
                        ? 'Retention'
                        : 'Audit Trail'}
          </button>))}
      </div>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (<div className="space-y-6">
          {/* Compliance Metrics Grid */}
          <div className="grid grid-cols-4 gap-6">
            <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-text-secondary text-sm font-medium">GDPR Compliance</span>
                <Shield className="w-4 h-4 text-border-glow"/>
              </div>
              <div className="text-4xl font-bold text-green-500">{metrics?.gdprCompliance}%</div>
              <p className="text-text-secondary text-sm mt-2">All requirements met</p>
            </div>

            <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-text-secondary text-sm font-medium">DPA Status</span>
                <CheckCircle className="w-4 h-4 text-green-500"/>
              </div>
              <div className="text-lg font-bold text-text">
                {metrics?.dpaSignedDate ? 'Signed' : 'Pending'}
              </div>
              <p className="text-text-secondary text-sm mt-2">
                {new Date(metrics?.dpaSignedDate || '').toLocaleDateString()}
              </p>
            </div>

            <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-text-secondary text-sm font-medium">Pending Requests</span>
                <AlertCircle className="w-4 h-4 text-yellow-500"/>
              </div>
              <div className="text-4xl font-bold text-yellow-500">{metrics?.pendingRequestsCount}</div>
              <p className="text-text-secondary text-sm mt-2">Require action</p>
            </div>

            <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-text-secondary text-sm font-medium">Last Audit</span>
                <Lock className="w-4 h-4 text-border-glow"/>
              </div>
              <div className="text-lg font-bold text-text">
                {new Date(metrics?.lastAuditDate || '').toLocaleDateString()}
              </div>
              <p className="text-text-secondary text-sm mt-2">110 days ago</p>
            </div>
          </div>

          {/* Compliance Checklist */}
          <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
            <h2 className="text-xl font-bold text-text mb-4">Compliance Checklist</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0"/>
                <div>
                  <p className="text-text font-medium">Privacy Policy</p>
                  <p className="text-sm text-text-secondary">Updated and published</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0"/>
                <div>
                  <p className="text-text font-medium">Data Processing Agreement (DPA)</p>
                  <p className="text-sm text-text-secondary">Signed with all processors</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0"/>
                <div>
                  <p className="text-text font-medium">Data Protection Impact Assessment (DPIA)</p>
                  <p className="text-sm text-text-secondary">Completed and documented</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0"/>
                <div>
                  <p className="text-text font-medium">Cookie Consent</p>
                  <p className="text-sm text-text-secondary">Implemented and tracked</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-lg bg-surface2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0"/>
                <div>
                  <p className="text-text font-medium">PII Redaction</p>
                  <p className="text-sm text-text-secondary">Active for all logs and transcripts</p>
                </div>
              </div>
            </div>
          </div>
        </div>)}

      {/* DATA REQUESTS TAB */}
      {activeTab === 'requests' && (<div className="space-y-6">
          <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
            <h2 className="text-xl font-bold text-text mb-4">Data Subject Requests</h2>
            <div className="space-y-3">
              {requests.map((request) => (<div key={request.id} className="flex items-start justify-between p-4 rounded-lg bg-surface2 border border-border/50">
                  <div className="flex items-start gap-4">
                    <div className="pt-1">{getRequestTypeIcon(request.type)}</div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-text">{request.id}</h3>
                        <span className={`text-xs font-bold ${getStatusColor(request.status)}`}>
                          {request.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-text-secondary mb-2">
                        From: {request.requestedBy}
                      </p>
                      <p className="text-xs text-text-secondary/60">
                        Submitted: {new Date(request.submittedAt).toLocaleDateString()} | Due:{' '}
                        {new Date(request.dueAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-text">{request.dataItems}</p>
                    <p className="text-xs text-text-secondary">data items</p>
                  </div>
                </div>))}
            </div>
          </div>
        </div>)}

      {/* RETENTION TAB */}
      {activeTab === 'retention' && (<div className="space-y-6">
          <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
            <h2 className="text-xl font-bold text-text mb-4">Data Retention Status</h2>
            <div className="space-y-4">
              {retentionStatus.map((item, idx) => (<div key={idx} className="p-4 rounded-lg bg-surface2 border border-border/50">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-text">{item.dataType}</h3>
                      <p className="text-sm text-text-secondary">Policy: {item.policy}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-text-secondary mb-1">Next purge: {item.nextPurgeDate}</p>
                      <p className="text-xs text-text-secondary/60">
                        {item.retainedRecords.toLocaleString()} / {item.totalRecords.toLocaleString()}{' '}
                        retained
                      </p>
                    </div>
                  </div>

                  {/* Progress Bars */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary/60 w-16">Retained:</span>
                      <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                        <div className="h-full bg-green-500" style={{
                    width: `${(item.retainedRecords / item.totalRecords) * 100}%`,
                }}></div>
                      </div>
                      <span className="text-xs text-text-secondary/60">
                        {((item.retainedRecords / item.totalRecords) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary/60 w-16">Purged:</span>
                      <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                        <div className="h-full bg-yellow-500" style={{
                    width: `${(item.purgedRecords / item.totalRecords) * 100}%`,
                }}></div>
                      </div>
                      <span className="text-xs text-text-secondary/60">
                        {((item.purgedRecords / item.totalRecords) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>))}
            </div>
          </div>
        </div>)}

      {/* AUDIT TRAIL TAB */}
      {activeTab === 'audit' && (<div className="space-y-6">
          <div className="bg-surface border border-border rounded-lg p-6 backdrop-blur-sm">
            <h2 className="text-xl font-bold text-text mb-4">Audit Trail</h2>
            <div className="space-y-2 text-sm text-text-secondary">
              <div className="p-3 rounded-lg bg-surface2 border border-border/50">
                <p className="font-medium text-text">2026-03-12 14:32:15</p>
                <p>DSR-20260312-001 status changed to IN_PROGRESS by admin@sailly.tech</p>
              </div>
              <div className="p-3 rounded-lg bg-surface2 border border-border/50">
                <p className="font-medium text-text">2026-03-11 09:15:43</p>
                <p>New DSR-20260311-002 created: DELETE request from customer@example.de</p>
              </div>
              <div className="p-3 rounded-lg bg-surface2 border border-border/50">
                <p className="font-medium text-text">2026-03-10 16:22:01</p>
                <p>Automatic purge executed: 6,810 call transcripts deleted (>90 days old)</p>
              </div>
              <div className="p-3 rounded-lg bg-surface2 border border-border/50">
                <p className="font-medium text-text">2026-03-08 11:08:32</p>
                <p>PII redaction audit: 45,230 transcripts scanned for PII</p>
              </div>
            </div>
          </div>
        </div>)}
    </div>);
}
