"use client";

import { useState, useEffect } from "react";
import {
  Shield, Activity, AlertTriangle, CheckCircle, Clock, Zap, Play,
  Menu, Search, User, Bell, ChevronRight, Calculator, Terminal,
  Cpu, Lock, Database, Globe
} from "lucide-react";

import { AttackGraph } from "../components/AttackGraph";
import { StatCard } from "../components/StatCard";
import { TerminalFeed } from "../components/TerminalFeed";
import { AgentGrid } from "../components/AgentGrid";

// Types
interface ThreatEvent {
  id: string;
  timestamp: string;
  severity: "low" | "medium" | "high" | "critical";
  type: string;
  source: string;
  status: "detected" | "analyzing" | "remediating" | "resolved";
  riskScore: number;
}

interface AgentUpdate {
  id?: string;
  timestamp: string;
  agent: string;
  status: string;
  message: string;
  severity: string;
  is_background?: boolean;
}

interface ApprovalRequest {
  type: string;
  action: string;
  target: string;
  risk_score: number;
}

interface GraphData {
  nodes: any[];
  edges: any[];
}

export default function Dashboard() {
  const [logs, setLogs] = useState<AgentUpdate[]>([]);
  const [backgroundLogs, setBackgroundLogs] = useState<AgentUpdate[]>([]);
  const [running, setRunning] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [approvalRequest, setApprovalRequest] = useState<ApprovalRequest | null>(null);
  const [blastRadius, setBlastRadius] = useState<GraphData | null>(null);
  const [activeTab, setActiveTab] = useState<'incidents' | 'telemetry'>('incidents');
  const [currentTime, setCurrentTime] = useState<string>("");

  // Stats
  const [stats, setStats] = useState({
    activeThreats: 0,
    resolved: 0,
    avgResponseTime: "0.0s",
    agentsActive: 0,
  });

  useEffect(() => {
    // Clock
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString()), 1000);

    // Connect to Python backend via WebSocket on 9004
    const socket = new WebSocket("ws://localhost:9004/ws/threat-feed");

    socket.onopen = () => {
      console.log("Connected to A-SOC Python Backend");
      setStats(prev => ({ ...prev, agentsActive: 6 }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "APPROVAL_REQUIRED") {
        setApprovalRequest(data);
        return;
      }

      if (data.type === "BLAST_RADIUS_UPDATE") {
        setBlastRadius(data.graph);
        return;
      }

      if (data.agent) {
        if (data.is_background) {
          setBackgroundLogs(prev => [data, ...prev].slice(0, 50));
        } else {
          setLogs((prev) => [data, ...prev]);
          setActiveTab('incidents');
        }

        if (!data.is_background) {
          if (data.severity === "high" || data.severity === "critical") {
            setStats(prev => ({ ...prev, activeThreats: prev.activeThreats + 1 }));
          }
          if (data.status === "success" || data.status === "logged") {
            setStats(prev => ({ ...prev, resolved: prev.resolved + 1, activeThreats: Math.max(0, prev.activeThreats - 1) }));
          }
        }
      }
    };

    setWs(socket);

    return () => {
      socket.close();
      clearInterval(timer);
    };
  }, []);

  const runSimulation = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      setRunning(true);
      setLogs([]);
      setBlastRadius(null);
      ws.send("START_SIMULATION");
    }
  };

  const approveAction = () => {
    if (ws) {
      ws.send("APPROVE_ACTION");
      setApprovalRequest(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 font-sans selection:bg-cyan-500/30 overflow-hidden relative">
      <div className="absolute inset-0 cyber-grid opacity-30 pointer-events-none"></div>
      <div className="absolute inset-0 scanlines opacity-50 pointer-events-none"></div>

      {/* Layout Grid */}
      <div className="flex h-screen">

        {/* Sidebar */}
        <aside className="w-20 lg:w-64 bg-slate-900/50 backdrop-blur-xl border-r border-slate-800 flex flex-col z-20 transition-all duration-300">
          <div className="p-6 flex items-center gap-3 border-b border-slate-800/50">
            <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
              <Shield className="w-6 h-6 text-cyan-400 animate-pulse-slow" />
            </div>
            <span className="font-bold text-xl tracking-tighter text-white hidden lg:block">
              A-SOC <span className="text-cyan-500">PRO</span>
            </span>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            {[
              { icon: Activity, label: "Live Monitoring", active: true },
              { icon: Database, label: "Asset Inventory", active: false },
              { icon: Terminal, label: "Forensics Lab", active: false },
              { icon: Globe, label: "Threat Intel", active: false },
              { icon: Lock, label: "Governance", active: false },
            ].map((item, i) => (
              <button
                key={i}
                className={`w-full flex items-center gap-4 p-3 rounded-lg transition-all group ${item.active
                  ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-[0_0_15px_-5px_rgba(6,182,212,0.3)]"
                  : "text-slate-500 hover:bg-slate-800 hover:text-slate-200"}`}
              >
                <item.icon className="w-5 h-5" />
                <span className="hidden lg:block font-medium text-sm">{item.label}</span>
                {item.active && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_5px_cyan] hidden lg:block"></div>}
              </button>
            ))}
          </nav>

          <div className="p-4 border-t border-slate-800/50">
            <div className="bg-slate-950/50 rounded-xl p-4 border border-slate-800">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600"></div>
                <div className="hidden lg:block">
                  <p className="text-sm font-bold text-white">Chief Operator</p>
                  <p className="text-xs text-slate-500">SEC-OPS LEVEL 5</p>
                </div>
              </div>
              <div className="text-[10px] text-slate-500 font-mono hidden lg:block">
                SESSION ID: {Math.random().toString(36).substring(7).toUpperCase()}
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col relative z-10 overflow-hidden">

          {/* Top Bar */}
          <header className="h-16 border-b border-slate-800 bg-slate-900/30 backdrop-blur-sm flex items-center justify-between px-8">
            <div className="flex items-center gap-4 text-slate-400 text-sm">
              <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700">
                <Clock className="w-3 h-3 text-cyan-400" />
                <span className="font-mono text-cyan-100">{currentTime}</span>
              </span>
              <span className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/50 border border-slate-700">
                <Globe className="w-3 h-3 text-emerald-400" />
                US-EAST-1
              </span>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={runSimulation}
                disabled={running}
                className={`cyber-button flex items-center gap-2 text-sm !py-2 !px-4 ${running ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {running ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {running ? "SYSTEM ACTIVE" : "INITIATE SIMULATION"}
              </button>
              <div className="w-px h-6 bg-slate-800"></div>
              <button className="relative p-2 text-slate-400 hover:text-white transition-colors">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
              </button>
            </div>
          </header>

          {/* Dashboard Content */}
          <div className="flex-1 p-8 overflow-y-auto no-scrollbar space-y-6">

            {/* KPI Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard
                icon={AlertTriangle}
                label="Active Threats"
                value={stats.activeThreats.toString()}
                subValue="+200%"
                color="red"
              />
              <StatCard
                icon={CheckCircle}
                label="Threats Neutralized"
                value={stats.resolved.toString()}
                subValue="Today"
                color="emerald"
              />
              <StatCard
                icon={Clock}
                label="Mean Time to Respond"
                value="1.2s"
                subValue="-0.4s"
                color="cyan"
              />
              <StatCard
                icon={Cpu}
                label="AI Agents Online"
                value={`${stats.agentsActive}/6`}
                subValue="Optimal"
                color="purple"
              />
            </div>

            {/* Central Visuals Row */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[450px]">
              {/* Attack Graph */}
              <div className="lg:col-span-8 cyber-card">
                <div className="absolute top-4 left-4 z-10">
                  <h3 className="text-white font-bold flex items-center gap-2">
                    <Activity className="w-4 h-4 text-orange-400" />
                    BLAST RADIUS VISUALIZATION
                  </h3>
                  <p className="text-slate-500 text-xs font-mono uppercase mt-1">Real-time vector analysis</p>
                </div>
                {blastRadius ? (
                  <div className="w-full h-full p-4">
                    <AttackGraph data={blastRadius} />
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center flex-col gap-4 opacity-30">
                    <Globe className="w-24 h-24 text-cyan-500 animate-pulse" />
                    <p className="font-mono text-cyan-500 tracking-widest">AWAITING TELEMETRY...</p>
                  </div>
                )}
              </div>

              {/* Right Panel: Agent Status */}
              <div className="lg:col-span-4 flex flex-col gap-6">
                <div className="flex-1 cyber-card p-4">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-white font-bold text-sm uppercase tracking-wider">Agent Health</h3>
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-cyan-500"></div>
                      <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                    </div>
                  </div>
                  {/* We'll inline grid here for simplicity or import AgentGrid if available */}
                  <AgentGrid running={running} />
                </div>
              </div>
            </div>

            {/* Bottom Row: Terminal Feeds */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[400px]">
              <TerminalFeed
                title="INCIDENT LOG STREAM"
                logs={logs}
                color="red"
                icon={AlertTriangle}
              />
              <TerminalFeed
                title="SYSTEM TELEMETRY (BACKGROUND)"
                logs={backgroundLogs}
                color="cyan"
                icon={Terminal}
              />
            </div>

          </div>
        </main>
      </div>

      {/* Approval Modal Overlay */}
      {approvalRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="relative w-full max-w-lg cyber-card border-red-500/50 shadow-[0_0_50px_-10px_rgba(239,68,68,0.5)]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-600 to-orange-600 animate-scan"></div>

            <div className="p-8">
              <div className="flex items-start gap-6">
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 animate-pulse">
                  <AlertTriangle className="w-10 h-10" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white tracking-tight">Authorization Required</h2>
                  <p className="text-red-400 font-mono text-xs uppercase tracking-wider mt-1">Severity Level: CRITICAL</p>
                  <p className="text-slate-400 mt-4 text-sm leading-relaxed">
                    The autonomous supervisor has intercepted a high-risk action proposed by the Response Agent. Manual authorization is required to proceed.
                  </p>
                </div>
              </div>

              <div className="mt-8 space-y-3 bg-red-950/20 p-4 rounded-lg border border-red-500/20 font-mono text-sm">
                <div className="flex justify-between border-b border-red-500/10 pb-2">
                  <span className="text-slate-500">PROPOSED ACTION</span>
                  <span className="text-white font-bold">{approvalRequest.action}</span>
                </div>
                <div className="flex justify-between border-b border-red-500/10 pb-2">
                  <span className="text-slate-500">TARGET RESOURCE</span>
                  <span className="text-white">{approvalRequest.target}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">RISK SCORE</span>
                  <span className="text-red-400 font-bold">{(approvalRequest.risk_score * 100).toFixed(1)}%</span>
                </div>
              </div>

              <div className="mt-8 flex gap-4">
                <button
                  onClick={() => setApprovalRequest(null)}
                  className="flex-1 py-3 px-4 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition-all font-bold uppercase tracking-wider text-sm"
                >
                  Deny Action
                </button>
                <button
                  onClick={approveAction}
                  className="flex-1 py-3 px-4 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold uppercase tracking-wider text-sm shadow-lg shadow-red-500/20 flex justify-center items-center gap-2 group"
                >
                  <span>Authorize</span>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
