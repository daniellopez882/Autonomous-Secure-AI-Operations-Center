"use client";

import { useEffect, useRef, useState } from "react";
import { Shield, Server, Database, User, Globe } from "lucide-react";

interface Node {
    id: string;
    type: string;
    label: string;
    risk: string;
}

interface Edge {
    source: string;
    target: string;
    label: string;
}

interface GraphData {
    nodes: Node[];
    edges: Edge[];
}

export function AttackGraph({ data }: { data: GraphData }) {
    if (!data) return null;

    // Fixed positions for known core nodes, fallback to grid/random for others
    const basePositions: Record<string, { x: number; y: number }> = {
        "attacker-ip": { x: 100, y: 150 },
        "user": { x: 300, y: 150 },
        "compromised-user": { x: 300, y: 150 },
        "insider": { x: 300, y: 150 },
        "c2-server": { x: 100, y: 150 },
    };

    // Calculate dynamic positions for any nodes not in basePositions
    const positions: Record<string, { x: number; y: number }> = { ...basePositions };

    data.nodes.forEach((node, i) => {
        if (!positions[node.id]) {
            // Assign a position on the right side if it's likely a resource/target
            const offset = i * 40;
            positions[node.id] = {
                x: 500,
                y: 80 + (i * 70)
            };
        }
    });

    const getIcon = (type: string) => {
        switch (type) {
            case "threat_actor": return <Globe className="w-5 h-5 text-red-500" />;
            case "identity": return <User className="w-5 h-5 text-orange-400" />;
            case "resource": return <Database className="w-5 h-5 text-yellow-400" />;
            default: return <Server className="w-5 h-5 text-blue-400" />;
        }
    };

    const getColor = (risk: string) => {
        switch (risk) {
            case "critical": return "stroke-red-500 fill-red-500/20";
            case "high": return "stroke-orange-500 fill-orange-500/20";
            case "medium": return "stroke-yellow-500 fill-yellow-500/20";
            default: return "stroke-blue-500 fill-blue-500/20";
        }
    };

    return (
        <div className="w-full h-full relative bg-slate-950/50 rounded-xl border border-slate-800 overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900/10 via-slate-950 to-slate-950"></div>

            <svg className="w-full h-full min-h-[300px]" viewBox="0 0 600 300">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
                    </marker>
                </defs>

                {/* Edges */}
                {data.edges.map((edge, i) => {
                    const start = positions[edge.source] || { x: 300, y: 150 };
                    const end = positions[edge.target] || { x: 300, y: 150 };
                    return (
                        <g key={i} className="animate-fade-in" style={{ animationDelay: `${i * 0.5}s` }}>
                            <line
                                x1={start.x}
                                y1={start.y}
                                x2={end.x}
                                y2={end.y}
                                stroke="#475569"
                                strokeWidth="2"
                                markerEnd="url(#arrowhead)"
                                className="animate-draw-line"
                            />
                            <text
                                x={(start.x + end.x) / 2}
                                y={(start.y + end.y) / 2 - 10}
                                textAnchor="middle"
                                fill="#94a3b8"
                                fontSize="10"
                                className="font-mono uppercase"
                            >
                                {edge.label}
                            </text>
                        </g>
                    );
                })}

                {/* Nodes */}
                {data.nodes.map((node, i) => {
                    const pos = positions[node.id] || { x: 300, y: 150 };
                    return (
                        <g key={node.id} className="animate-pop-in" style={{ animationDelay: `${i * 0.2}s` }}>
                            {/* Risk Glow */}
                            <circle cx={pos.x} cy={pos.y} r="30" className={`animate-pulse-slow ${getColor(node.risk).replace("stroke", "fill").replace("500", "500/10")}`} />

                            {/* Main Node */}
                            <circle cx={pos.x} cy={pos.y} r="20" className={`stroke-2 ${getColor(node.risk)} fill-slate-900`} />
                        </g>
                    );
                })}
            </svg>

            {/* HTML Overlay for Icons and Labels */}
            {data.nodes.map((node, i) => {
                const pos = positions[node.id] || { x: 300, y: 150 };
                return (
                    <div
                        key={node.id}
                        className="absolute flex flex-col items-center transform -translate-x-1/2 -translate-y-1/2 z-10 animate-pop-in"
                        style={{
                            left: `${(pos.x / 600) * 100}%`,
                            top: `${(pos.y / 300) * 100}%`,
                            animationDelay: `${i * 0.2}s`
                        }}
                    >
                        <div className="mb-8 pointer-events-none">
                            {getIcon(node.type)}
                        </div>
                        <div className="mt-8 bg-slate-900/90 px-2 py-1 rounded text-[10px] text-cyan-100 border border-cyan-500/30 whitespace-nowrap backdrop-blur-sm shadow-lg">
                            {node.label}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

