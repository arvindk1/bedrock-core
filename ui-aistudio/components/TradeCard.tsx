import React, { useState } from 'react';
import { TradeCandidate } from '../types';
import { ChevronDown, ChevronUp, AlertCircle, TrendingUp, DollarSign, Target } from 'lucide-react';

interface TradeCardProps {
  trade: TradeCandidate;
}

export const TradeCard: React.FC<TradeCardProps> = ({ trade }) => {
  const [expanded, setExpanded] = useState(false);

  const isCredit = trade.netPremium > 0;
  const premiumColor = isCredit ? 'text-emerald-400' : 'text-slate-300';
  const scoreColor = trade.gatekeeperScore >= 90 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 
                     trade.gatekeeperScore >= 80 ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' : 'bg-amber-500/20 text-amber-400 border-amber-500/30';

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-sm mb-3 overflow-hidden transition-all hover:border-slate-600 shadow-sm">
      {/* Card Header Summary */}
      <div 
        className="p-4 cursor-pointer flex items-center justify-between bg-gradient-to-r from-slate-900 to-slate-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-6">
          <div className="w-16">
            <span className="text-lg font-bold text-white block">{trade.symbol}</span>
            <span className="text-xs text-slate-500 font-mono">{trade.expiration}</span>
          </div>
          
          <div className="flex flex-col">
            <span className="text-xs text-slate-400 uppercase tracking-wider">Strategy</span>
            <span className="text-sm font-medium text-indigo-200">{trade.strategy}</span>
          </div>

          <div className="flex flex-col w-20">
             <span className="text-xs text-slate-400 uppercase tracking-wider">Net</span>
             <span className={`text-sm font-mono font-bold ${premiumColor}`}>
               {isCredit ? '+' : ''}{trade.netPremium.toFixed(2)}
             </span>
          </div>

           <div className="flex flex-col w-24">
             <span className="text-xs text-slate-400 uppercase tracking-wider">Max Risk</span>
             <span className="text-sm font-mono text-rose-400">-${trade.maxLoss}</span>
          </div>

          <div className="flex flex-col w-24">
             <span className="text-xs text-slate-400 uppercase tracking-wider">Score</span>
             <div className={`inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-mono font-bold border ${scoreColor}`}>
                {trade.gatekeeperScore}
             </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
           <div className="text-right flex flex-col items-end">
             <span className="text-xs text-slate-500 uppercase">DTE</span>
             <span className="text-sm font-mono text-slate-300">{trade.dte}d</span>
           </div>
           {expanded ? <ChevronUp className="text-slate-500" size={18} /> : <ChevronDown className="text-slate-500" size={18} />}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="bg-slate-950/50 border-t border-slate-800 p-4 grid grid-cols-12 gap-6 animate-in slide-in-from-top-2 duration-200">
          
          {/* Left: Legs */}
          <div className="col-span-7 border-r border-slate-800 pr-6">
            <h4 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-3">Leg Structure</h4>
            <div className="space-y-2">
              {trade.legs.map((leg, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm font-mono p-1.5 bg-slate-900/50 rounded-sm border border-slate-800/50">
                  <div className="flex items-center space-x-2">
                    <span className={`px-1.5 py-0.5 text-[10px] uppercase font-bold rounded-sm ${leg.side === 'Long' ? 'bg-emerald-900/30 text-emerald-400' : 'bg-rose-900/30 text-rose-400'}`}>
                      {leg.side}
                    </span>
                    <span className="text-slate-300">{leg.strike} {leg.type}</span>
                  </div>
                  <span className="text-slate-500">Δ {leg.delta.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Analytical Metrics */}
          <div className="col-span-5 space-y-4">
             <div>
                <h4 className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-3">Risk Profile</h4>
                <div className="grid grid-cols-2 gap-3">
                   <div className="p-2 bg-slate-900 rounded-sm border border-slate-800">
                      <div className="flex items-center space-x-2 mb-1">
                        <Target size={12} className="text-indigo-400"/>
                        <span className="text-xs text-slate-400">Breakeven</span>
                      </div>
                      <span className="text-sm font-mono text-slate-200">
                        {trade.breakeven.map(b => b.toFixed(2)).join(' / ')}
                      </span>
                   </div>
                   <div className="p-2 bg-slate-900 rounded-sm border border-slate-800">
                      <div className="flex items-center space-x-2 mb-1">
                        <AlertCircle size={12} className="text-indigo-400"/>
                        <span className="text-xs text-slate-400">Liq. Impact</span>
                      </div>
                      <span className="text-sm font-mono text-slate-200">
                        {(trade.liquidityImpact * 100).toFixed(2)}%
                      </span>
                   </div>
                </div>
             </div>

             <div className="flex justify-between items-center pt-2">
               <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-1.5 text-xs font-bold border border-slate-600 rounded-sm mr-2 transition-colors">
                  SIMULATE
               </button>
               <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-1.5 text-xs font-bold rounded-sm shadow-lg shadow-emerald-900/20 transition-colors">
                  EXECUTE ORDER
               </button>
             </div>
          </div>

        </div>
      )}
    </div>
  );
};
