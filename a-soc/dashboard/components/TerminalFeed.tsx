import { Shield, Server } from "lucide-react";
import { useEffect, useRef } from "react";

interface Log {
    agent: string;
    status: string;
    message: string;
    severity: string;
    timestamp: string;
}

interface TerminalFeedProps {
    logs: Log[];
    title: string;
    color?: "cyan" | "orange" | "red";
    icon?: any;
}

export function TerminalFeed({ logs, title, color = "cyan", icon: Icon = Shield }: TerminalFeedProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const severityColor = (severity: string) => {
        switch (severity) {
            case "critical": return "text-red-500 bg-red-500/10 border-red-500/20";
            case "high": return "text-orange-500 bg-orange-500/10 border-orange-500/20";
            case "medium": return "text-yellow-500 bg-yellow-500/10 border-yellow-500/20";
            default: return "text-cyan-500 bg-cyan-500/10 border-cyan-500/20";
        }
    };

    return (
        <div className="cyber-card flex flex-col h-full min-h-[500px] border border-slate-800">
            {/* Header Bar */}
            <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex items-center justify-between backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded bg-${color}-500/10 border border-${color}-500/20`}>
                        <Icon className={`w-4 h-4 text-${color}-400`} />
                    </div>
                    <span className="font-mono text-sm uppercase tracking-widest text-slate-300 font-bold">
                        {title}
                    </span>
                </div>

                {/* Fake Window Controls */}
                <div className="flex gap-2">
                    <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                    <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                    <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                </div>
            </div>

            {/* Terminal Viewport */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 font-mono text-xs sm:text-sm space-y-2 terminal-scrollbar bg-black/40">
                {logs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-4 animate-pulse">
                        <Server className="w-12 h-12 opacity-20" />
                        <p>System initialized. Waiting for input stream...</p>
                    </div>
                ) : (
                    logs.map((log, i) => (
                        <div key={i} className="group flex gap-3 animate-fade-in-up hover:bg-slate-900/50 p-1 -mx-1 rounded transition-colors">
                            <span className="text-cyan-600 w-20 shrink-0 select-none font-bold">
                                [{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}]
                            </span>

                            <div className="flex-1 break-words">
                                <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] uppercase font-bold mr-2 ${severityColor(log.severity)}`}>
                                    {log.agent}::{log.status}
                                </span>
                                <span className="text-slate-100 font-mono tracking-wide group-hover:text-white transition-colors">
                                    {log.message}
                                </span>
                            </div>
                        </div>
                    ))
                )}

                {/* Blinking Cursor at bottom */}
                <div className="h-4 w-2 bg-cyan-500 animate-blink mt-2 inline-block"></div>
            </div>

            {/* Footer Status Bar */}
            <div className="bg-slate-950 px-4 py-1.5 border-t border-slate-800 text-[10px] font-mono text-slate-500 flex justify-between uppercase tracking-wider">
                <span>Channel: Secure/WSS-9004</span>
                <span className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${logs.length > 0 ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`}></span>
                    Live
                </span>
            </div>
        </div>
    );
}
