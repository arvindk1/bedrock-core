import React, { useState } from 'react';
import { TradeCandidate } from '../types';
import { ChevronDown, ChevronRight, Target, AlertCircle } from 'lucide-react';

interface TradeTableProps {
  trades: TradeCandidate[];
}

export const TradeTable: React.FC<TradeTableProps> = ({ trades }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-sm overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 bg-slate-950 p-3 text-[10px] text-slate-500 uppercase font-bold border-b border-slate-800 items-center">
            <div className="col-span-1"></div>
            <div className="col-span-2">Symbol / Strategy</div>
            <div className="col-span-2">Expiration</div>
            <div className="col-span-1 text-right">Net</div>
            <div className="col-span-1 text-right">Max Risk</div>
            <div className="col-span-1 text-right">Max Profit</div>
            <div className="col-span-2 text-center">Score</div>
            <div className="col-span-2 text-right">Impact</div>
        </div>

        {/* Table Body */}
        {trades.map(trade => {
            const isExpanded = expandedId === trade.id;
            const isCredit = trade.netPremium > 0;
            const scoreColor = trade.gatekeeperScore >= 90 ? 'text-emerald-400' : 'text-amber-400';

            return (
                <div key={trade.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 transition-colors">
                    {/* Row Summary */}
                    <div 
                        className="grid grid-cols-12 gap-2 p-3 items-center cursor-pointer"
                        onClick={() => toggleExpand(trade.id)}
                    >
                        <div className="col-span-1 flex justify-center text-slate-500">
                             {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </div>
                        <div className="col-span-2">
                             <div className="text-sm font-bold text-slate-200">{trade.symbol}</div>
                             <div className="text-[10px] text-slate-500 uppercase truncate">{trade.strategy}</div>
                        </div>
                         <div className="col-span-2">
                             <div className="text-xs font-mono text-slate-300">{trade.expiration}</div>
                             <div className="text-[10px] text-slate-500">{trade.dte} DTE</div>
                        </div>
                         <div className={`col-span-1 text-right text-xs font-mono font-bold ${isCredit ? 'text-emerald-400' : 'text-slate-300'}`}>
                             {isCredit ? '+' : ''}{trade.netPremium.toFixed(2)}
                        </div>
                        <div className="col-span-1 text-right text-xs font-mono text-rose-400">
                             {trade.maxLoss}
                        </div>
                        <div className="col-span-1 text-right text-xs font-mono text-emerald-400">
                             {trade.maxProfit}
                        </div>
                         <div className="col-span-2 flex justify-center">
                             <span className={`text-xs font-mono font-bold px-2 py-0.5 border rounded-[2px] ${scoreColor} border-current bg-opacity-10 bg-slate-500`}>
                                 {trade.gatekeeperScore}
                             </span>
                        </div>
                        <div className="col-span-2 text-right text-xs font-mono text-slate-400">
                            {(trade.liquidityImpact * 100).toFixed(2)}%
                        </div>
                    </div>

                    {/* Expanded Detail Panel */}
                    {isExpanded && (
                        <div className="bg-slate-950/50 p-4 border-t border-slate-800 grid grid-cols-2 gap-6 animate-in slide-in-from-top-1">
                             {/* Legs */}
                             <div>
                                 <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Structure</h4>
                                 <div className="space-y-1">
                                    {trade.legs.map((leg, idx) => (
                                        <div key={idx} className="flex justify-between text-xs font-mono p-1 border-b border-slate-800/50 last:border-0">
                                            <span className={leg.side === 'Long' ? 'text-emerald-400' : 'text-rose-400'}>{leg.side} {leg.strike} {leg.type}</span>
                                            <span className="text-slate-500">Δ {leg.delta}</span>
                                        </div>
                                    ))}
                                 </div>
                             </div>
                             
                             {/* Stats */}
                             <div>
                                 <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Simulated Impact</h4>
                                 <div className="grid grid-cols-2 gap-2">
                                     <div className="bg-slate-900 p-2 rounded-sm border border-slate-800">
                                        <span className="block text-[10px] text-slate-500">Portfolio Delta</span>
                                        <span className="text-xs font-mono text-slate-300">{trade.postTradeImpact?.portfolioDelta}</span>
                                     </div>
                                      <div className="bg-slate-900 p-2 rounded-sm border border-slate-800">
                                        <span className="block text-[10px] text-slate-500">Breakeven</span>
                                        <span className="text-xs font-mono text-slate-300">{trade.breakeven.join(' / ')}</span>
                                     </div>
                                 </div>
                                 <div className="mt-3 flex gap-2">
                                     <button className="w-full bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold py-1.5 rounded-sm transition-colors">EXECUTE</button>
                                     <button className="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold py-1.5 rounded-sm transition-colors">ANALYZE</button>
                                 </div>
                             </div>
                        </div>
                    )}
                </div>
            );
        })}
    </div>
  );
};
