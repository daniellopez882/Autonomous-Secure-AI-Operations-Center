import { LucideIcon } from "lucide-react";

interface StatCardProps {
    icon: LucideIcon;
    label: string;
    value: string;
    subValue?: string;
    color: "cyan" | "purple" | "rose" | "emerald" | "red" | "blue" | "green" | "orange";
    trend?: "up" | "down" | "neutral";
}

export function StatCard({ icon: Icon, label, value, subValue, color, trend }: StatCardProps) {
    const colors = {
        cyan: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
        purple: "text-purple-400 border-purple-500/30 bg-purple-500/5",
        rose: "text-rose-400 border-rose-500/30 bg-rose-500/5",
        emerald: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
        // Fallbacks
        red: "text-rose-400 border-rose-500/30 bg-rose-500/5",
        blue: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
        green: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
        orange: "text-orange-400 border-orange-500/30 bg-orange-500/5",
    };

    const glowColors: Record<string, string> = {
        cyan: "shadow-[0_0_20px_-5px_rgba(34,211,238,0.3)]",
        purple: "shadow-[0_0_20px_-5px_rgba(168,85,247,0.3)]",
        rose: "shadow-[0_0_20px_-5px_rgba(251,113,133,0.3)]",
        emerald: "shadow-[0_0_20px_-5px_rgba(52,211,153,0.3)]",
        // Fallbacks
        red: "shadow-[0_0_20px_-5px_rgba(251,113,133,0.3)]",
        blue: "shadow-[0_0_20px_-5px_rgba(34,211,238,0.3)]",
        green: "shadow-[0_0_20px_-5px_rgba(52,211,153,0.3)]",
        orange: "shadow-[0_0_20px_-5px_rgba(251,146,60,0.3)]",
    };

    return (
        <div className={`cyber-card p-6 flex items-center justify-between group hover:scale-[1.02] transition-transform ${glowColors[color]}`}>
            <div className="relative z-10">
                <h3 className="text-slate-300 text-xs font-mono uppercase tracking-widest mb-1">{label}</h3>
                <div className="text-3xl font-bold text-white tracking-tight flex items-baseline gap-2">
                    {value}
                    {subValue && <span className="text-sm font-normal text-slate-400">{subValue}</span>}
                </div>

                {/* Decorative corner accents */}
                <div className={`absolute -top-2 -left-2 w-3 h-3 border-t border-l ${colors[color].split(' ')[1]} opacity-50`}></div>
                <div className={`absolute -bottom-2 -left-2 w-3 h-3 border-b border-l ${colors[color].split(' ')[1]} opacity-50`}></div>
            </div>

            <div className={`p-4 rounded-xl border ${colors[color]} relative overflow-hidden group-hover:animate-pulse-fast`}>
                <div className="absolute inset-0 bg-gradient-to-tr from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <Icon className={`w-8 h-8 ${colors[color].split(' ')[0]}`} />
            </div>

            {/* Background Grid Pattern for Card */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{ backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '8px 8px' }}>
            </div>
        </div>
    );
}
