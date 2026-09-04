"use client";

import { Activity, Cpu, Database, FileText, Lock, Radio } from "lucide-react";
import { useEffect, useState } from "react";

/*
 * Load figures and PIDs used to be generated with Math.random() directly in the
 * render body. Under Next.js SSR the server and the client produce different
 * numbers, so React reports a hydration mismatch and discards the server markup
 * -- and every unrelated re-render reshuffled the values.
 *
 * Load is state seeded at each agent's base value and refreshed only from an
 * interval callback, so the server render is deterministic. PIDs are derived
 * from the agent id instead: nothing needed them to be unpredictable, only
 * stable.
 */

const AGENTS = [
    { id: "telemetry", name: "Telemetry", icon: Radio, col: "col-span-2 row-span-2", base: 85, jitter: 5 },
    { id: "detection", name: "Detection", icon: Activity, col: "col-span-1 row-span-1", base: 90, jitter: 8 },
    { id: "supervisor", name: "Supervisor", icon: Lock, col: "col-span-1 row-span-1", base: 40, jitter: 10 },
    { id: "forensics", name: "Forensics", icon: FileText, col: "col-span-1 row-span-1", base: 60, jitter: 20 },
    { id: "response", name: "Response", icon: Cpu, col: "col-span-1 row-span-1", base: 30, jitter: 50 },
    { id: "compliance", name: "Compliance", icon: Database, col: "col-span-2 row-span-1", base: 12, jitter: 0 },
] as const;

const REFRESH_MS = 1500;

/**
 * A stable, plausible-looking PID derived from the agent id.
 *
 * These were Math.floor(Math.random() * 9000 + 1000) evaluated in the render
 * body, so they differed between the server and client render and reshuffled
 * on every unrelated re-render. Nothing needs them to be unpredictable -- only
 * stable.
 */
function pseudoPid(id: string): number {
    let hash = 0;
    for (let i = 0; i < id.length; i += 1) {
        hash = (hash * 31 + id.charCodeAt(i)) % 9000;
    }
    return 1000 + hash;
}

function statusColor(load: number, running: boolean): string {
    if (!running) return "border-slate-800 bg-slate-900/50 text-slate-600";
    if (load > 80) return "border-red-500/50 bg-red-500/10 text-red-400 animate-pulse";
    if (load > 50) return "border-orange-500/50 bg-orange-500/10 text-orange-400";
    return "border-emerald-500/50 bg-emerald-500/10 text-emerald-400";
}

export function AgentGrid({ running }: { running: boolean }) {
    // Seeded at their base values, so the server render is deterministic.
    const [jitter, setJitter] = useState<Record<string, number>>(() =>
        Object.fromEntries(AGENTS.map((a) => [a.id, a.base])),
    );

    useEffect(() => {
        if (!running) return;
        // Only the interval callback sets state; nothing is set synchronously
        // in the effect body, which would cause a cascading render.
        const handle = setInterval(
            () =>
                setJitter(
                    Object.fromEntries(
                        AGENTS.map((a) => [a.id, a.base + Math.random() * a.jitter]),
                    ),
                ),
            REFRESH_MS,
        );
        return () => clearInterval(handle);
    }, [running]);

    return (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 h-full min-h-[300px]">
            {AGENTS.map((agent) => {
                // Derived, not stored: an idle agent reads zero without
                // needing an effect to write it.
                const load = running ? (jitter[agent.id] ?? agent.base) : 0;
                const Icon = agent.icon;
                const pid = pseudoPid(agent.id);

                return (
                    <div
                        key={agent.id}
                        className={`
              relative p-4 rounded-xl border transition-all duration-500 flex flex-col justify-between overflow-hidden group
              ${agent.col}
              ${statusColor(load, running)}
            `}
                    >
                        {/* Background data-stream effect */}
                        <div
                            className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 transition-transform duration-1000 ${running ? "scale-150 rotate-45" : "scale-100"}`}
                        />

                        <div className="flex justify-between items-start relative z-10">
                            <Icon
                                className={`w-6 h-6 ${running && load > 80 ? "animate-bounce" : ""}`}
                                aria-hidden="true"
                            />
                            <div className="text-[10px] uppercase font-mono tracking-widest opacity-90 text-cyan-200">
                                PID: {pid}
                            </div>
                        </div>

                        <div className="relative z-10 mt-auto">
                            <div className="flex justify-between items-end mb-2">
                                <span className="font-bold text-sm tracking-wide text-white">
                                    {agent.name}
                                </span>
                                <span className="font-mono text-xs text-cyan-300">
                                    {load.toFixed(0)}% LOAD
                                </span>
                            </div>

                            <div
                                className="h-1.5 bg-slate-800/50 rounded-full overflow-hidden"
                                role="progressbar"
                                aria-label={`${agent.name} load`}
                                aria-valuenow={Math.round(load)}
                                aria-valuemin={0}
                                aria-valuemax={100}
                            >
                                <div
                                    className={`h-full transition-all duration-1000 ease-out ${load > 80 ? "bg-red-500" : load > 50 ? "bg-orange-500" : "bg-emerald-500"}`}
                                    style={{ width: `${Math.min(load, 100)}%` }}
                                />
                            </div>
                        </div>

                        <div className="absolute inset-0 border-2 border-transparent group-hover:border-white/10 rounded-xl transition-all pointer-events-none" />
                    </div>
                );
            })}
        </div>
    );
}
