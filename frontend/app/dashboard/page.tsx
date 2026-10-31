'use client';

import { useEffect, useState } from 'react';
import { Shield, FileText, Users, Camera, AlertTriangle, MapPin, Bot, LogOut, Activity } from 'lucide-react';
import Link from 'next/link';
import { adminAPI, casesAPI } from '@/lib/api';

interface DashboardStats {
  active_cases: number;
  officers_on_duty: number;
  unreviewed_high_threats: number;
}

interface Officer {
  full_name: string;
  rank: string;
  badge_number: string;
  is_on_duty: boolean;
  threat_level: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [officer, setOfficer] = useState<Officer | null>(null);
  const [recentCases, setRecentCases] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    const officerData = localStorage.getItem('shield_officer');
    if (!officerData) { window.location.href = '/login'; return; }
    setOfficer(JSON.parse(officerData));
    
    // Load dashboard data
    adminAPI.dashboard().then(r => setStats(r.data)).catch(() => {});
    casesAPI.list({ per_page: 5 }).then(r => setRecentCases(r.data.cases || [])).catch(() => {});
  }, []);

  const handleLogout = async () => {
    try { await fetch('/api/v1/auth/logout', { method: 'POST' }); } catch {}
    localStorage.clear();
    window.location.href = '/login';
  };

  const threatColor = {
    LOW: 'text-green-400 bg-green-900/30',
    MEDIUM: 'text-yellow-400 bg-yellow-900/30',
    HIGH: 'text-orange-400 bg-orange-900/30',
    CRITICAL: 'text-red-400 bg-red-900/30',
  }[officer?.threat_level || 'LOW'] || 'text-green-400';

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white">SHIELD</h1>
              <p className="text-xs text-gray-400">Law Enforcement Platform</p>
            </div>
          </div>
        </div>

        {/* Officer Info */}
        <div className="p-4 border-b border-gray-800">
          <div className="bg-gray-800 rounded-xl p-3">
            <p className="text-sm font-medium text-white">{officer?.full_name}</p>
            <p className="text-xs text-blue-400">{officer?.rank}</p>
            <p className="text-xs text-gray-500">{officer?.badge_number}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${threatColor}`}>
                Threat: {officer?.threat_level}
              </span>
              {officer?.is_on_duty && (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-green-900/30 text-green-400">
                  ON DUTY
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {[
            { icon: Activity, label: 'Dashboard', href: '/dashboard', active: true },
            { icon: FileText, label: 'My Cases', href: '/dashboard/cases' },
            { icon: Bot, label: 'ARIA AI', href: '/dashboard/ai' },
            { icon: MapPin, label: 'Live Map', href: '/dashboard/map' },
            { icon: Camera, label: 'CCTV', href: '/dashboard/cctv' },
            { icon: Users, label: 'Officers', href: '/dashboard/officers' },
            { icon: AlertTriangle, label: 'Threats', href: '/dashboard/threats' },
          ].map(({ icon: Icon, label, href, active }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>

        {/* Logout */}
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 text-gray-400 hover:text-red-400 hover:bg-red-900/20 rounded-xl text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white">Command Dashboard</h2>
          <p className="text-gray-400 text-sm mt-1">
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            label="Active Cases"
            value={stats?.active_cases ?? '—'}
            icon={<FileText className="w-5 h-5 text-blue-400" />}
            color="blue"
          />
          <StatCard
            label="Officers On Duty"
            value={stats?.officers_on_duty ?? '—'}
            icon={<Users className="w-5 h-5 text-green-400" />}
            color="green"
          />
          <StatCard
            label="Threat Alerts"
            value={stats?.unreviewed_high_threats ?? '—'}
            icon={<AlertTriangle className="w-5 h-5 text-orange-400" />}
            color="orange"
            urgent={Boolean(stats?.unreviewed_high_threats)}
          />
          <StatCard
            label="CCTV Cameras"
            value="Online"
            icon={<Camera className="w-5 h-5 text-purple-400" />}
            color="purple"
          />
        </div>

        {/* Recent Cases */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">Recent Cases</h3>
            <Link href="/dashboard/cases" className="text-blue-400 text-sm hover:text-blue-300">
              View all →
            </Link>
          </div>
          {recentCases.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No cases found</p>
          ) : (
            <div className="space-y-3">
              {recentCases.map((c: Record<string, unknown>) => (
                <Link
                  key={c.id as string}
                  href={`/dashboard/cases/${c.id}`}
                  className="flex items-center justify-between p-3 bg-gray-800 hover:bg-gray-750 rounded-xl transition-colors group"
                >
                  <div>
                    <p className="text-sm font-medium text-white group-hover:text-blue-300">
                      {c.case_number as string}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">{c.title as string}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${priorityColor(c.priority as string)}`}>
                      {c.priority as string}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-full ${statusColor(c.status as string)}`}>
                      {c.status as string}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, icon, color, urgent }: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  urgent?: boolean;
}) {
  const colors = {
    blue: 'border-blue-800 bg-blue-900/10',
    green: 'border-green-800 bg-green-900/10',
    orange: 'border-orange-800 bg-orange-900/10',
    purple: 'border-purple-800 bg-purple-900/10',
  };
  return (
    <div className={`bg-gray-900 border rounded-2xl p-5 ${colors[color as keyof typeof colors]} ${urgent ? 'animate-pulse' : ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm">{label}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className="p-2 bg-gray-800 rounded-xl">{icon}</div>
      </div>
    </div>
  );
}

function priorityColor(p: string) {
  return {
    LOW: 'bg-gray-700 text-gray-300',
    MEDIUM: 'bg-yellow-900/50 text-yellow-300',
    HIGH: 'bg-orange-900/50 text-orange-300',
    CRITICAL: 'bg-red-900/50 text-red-300',
    TOP_SECRET: 'bg-purple-900/50 text-purple-300',
  }[p] || 'bg-gray-700 text-gray-300';
}

function statusColor(s: string) {
  return {
    OPEN: 'bg-blue-900/50 text-blue-300',
    UNDER_INVESTIGATION: 'bg-indigo-900/50 text-indigo-300',
    CLOSED_SOLVED: 'bg-green-900/50 text-green-300',
    CLOSED_UNSOLVED: 'bg-gray-700 text-gray-400',
  }[s] || 'bg-gray-700 text-gray-300';
}
