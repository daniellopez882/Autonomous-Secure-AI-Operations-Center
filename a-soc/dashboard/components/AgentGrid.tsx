import { Activity, Radio, Cpu, Lock, FileText, Database } from "lucide-react";

interface AgentStatus {
    name: string;
    status: string;
    load: number;
}

const agents = [
    { id: "telemetry", name: "Telemetry", icon: Radio, col: "col-span-2 row-span-2" },
    { id: "detection", name: "Detection", icon: Activity, col: "col-span-1 row-span-1" },
    { id: "supervisor", name: "Supervisor", icon: Lock, col: "col-span-1 row-span-1" },
    { id: "forensics", name: "Forensics", icon: FileText, col: "col-span-1 row-span-1" },
    { id: "response", name: "Response", icon: Cpu, col: "col-span-1 row-span-1" },
    { id: "compliance", name: "Compliance", icon: Database, col: "col-span-2 row-span-1" },
];

export function AgentGrid({ running }: { running: boolean }) {
    const getStatusColor = (load: number) => {
        if (!running) return "border-slate-800 bg-slate-900/50 text-slate-600";
        if (load > 80) return "border-red-500/50 bg-red-500/10 text-red-400 animate-pulse";
        if (load > 50) return "border-orange-500/50 bg-orange-500/10 text-orange-400";
        return "border-emerald-500/50 bg-emerald-500/10 text-emerald-400";
    };

    const getLoad = (id: string) => {
        // Generate varied mock load for demo
        if (!running) return 0;
        switch (id) {
            case "telemetry": return 85 + Math.random() * 5;
            case "detection": return 90 + Math.random() * 8;
            case "supervisor": return 40 + Math.random() * 10;
            case "forensics": return 60 + Math.random() * 20;
            case "response": return 30 + Math.random() * 50; // Bursty
            default: return 12;
        }
    };

    return (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 h-full min-h-[300px]">
            {agents.map((agent) => {
                const load = getLoad(agent.id);
                const Icon = agent.icon;

                return (
                    <div
                        key={agent.id}
                        className={`
              relative p-4 rounded-xl border transition-all duration-500 flex flex-col justify-between overflow-hidden group
              ${agent.col}
              ${getStatusColor(load)}
            `}
                    >
                        {/* Background Data Stream Effect */}
                        <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 transition-transform duration-1000 ${running ? "scale-150 rotate-45" : "scale-100"}`}></div>

                        <div className="flex justify-between items-start relative z-10">
                            <Icon className={`w-6 h-6 ${running && load > 80 ? "animate-bounce" : ""}`} />
                            <div className="text-[10px] uppercase font-mono tracking-widest opacity-90 text-cyan-200">
                                PID: {Math.floor(Math.random() * 9000 + 1000)}
                            </div>
                        </div>

                        <div className="relative z-10 mt-auto">
                            <div className="flex justify-between items-end mb-2">
                                <span className="font-bold text-sm tracking-wide text-white">{agent.name}</span>
                                <span className="font-mono text-xs text-cyan-300">{load.toFixed(0)}% LOAD</span>
                            </div>

                            {/* Progress Bar */}
                            <div className="h-1.5 bg-slate-800/50 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-1000 ease-out ${load > 80 ? "bg-red-500" : load > 50 ? "bg-orange-500" : "bg-emerald-500"}`}
                                    style={{ width: `${load}%` }}
                                ></div>
                            </div>
                        </div>

                        {/* Hover Glitch Effect Border */}
                        <div className="absolute inset-0 border-2 border-transparent group-hover:border-white/10 rounded-xl transition-all pointer-events-none"></div>
                    </div>
                );
            })}
        </div>
    );
}
