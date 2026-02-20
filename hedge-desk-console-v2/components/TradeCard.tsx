import React, { useState } from 'react';
import { TradeCandidate } from '../types';
import { ChevronDown, ChevronUp, AlertCircle, TrendingUp, Target, BarChart2, PieChart } from 'lucide-react';

interface TradeCardProps {
  trade: TradeCandidate;
}

export const TradeCard: React.FC<TradeCardProps> = ({ trade }) => {
  const [expanded, setExpanded] = useState(false);

  const isCredit = trade.netPremium > 0;
  const premiumColor = isCredit ? 'text-emerald-400' : 'text-slate-300';
  const scoreColor = trade.gatekeeperScore >= 90 ? 'bg-emerald-950 text-emerald-400 border-emerald-800' : 
                     trade.gatekeeperScore >= 80 ? 'bg-indigo-950 text-indigo-400 border-indigo-800' : 'bg-amber-950 text-amber-400 border-amber-800';

  return (
    <div className={`bg-slate-900 border ${expanded ? 'border-slate-600' : 'border-slate-800'} rounded-sm mb-3 overflow-hidden transition-all hover:border-slate-600 shadow-sm group`}>
      {/* Card Header Summary */}
      <div 
        className="p-4 cursor-pointer flex items-center justify-between bg-gradient-to-r from-slate-900 to-slate-900"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-6">
          <div className="w-16">
            <span className="text-lg font-bold text-white block group-hover:text-indigo-300 transition-colors">{trade.symbol}</span>
            <span className="text-[10px] text-slate-500 font-mono uppercase">{trade.expiration}</span>
          </div>
          
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Strategy</span>
            <span className="text-sm font-medium text-slate-200">{trade.strategy}</span>
          </div>

          <div className="flex flex-col w-24">
             <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Net Premium</span>
             <span className={`text-sm font-mono font-bold ${premiumColor}`}>
               {isCredit ? '+' : ''}{trade.netPremium.toFixed(2)}
             </span>
          </div>

           <div className="flex flex-col w-24">
             <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Max Risk</span>
             <span className="text-sm font-mono text-rose-400">-${trade.maxLoss}</span>
          </div>

          <div className="flex flex-col w-24">
             <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Gate Score</span>
             <div className={`inline-flex items-center justify-center px-2 py-0.5 rounded-[2px] text-xs font-mono font-bold border ${scoreColor}`}>
                {trade.gatekeeperScore}
             </div>
          </div>
        </div>

        <div className="flex items-center space-x-6">
           <div className="text-right flex flex-col items-end">
             <span className="text-[10px] text-slate-500 uppercase font-bold">Liquidity Impact</span>
             <span className="text-xs font-mono text-slate-300">
               {(trade.liquidityImpact * 100).toFixed(2)}%
             </span>
           </div>
           {expanded ? <ChevronUp className="text-slate-500" size={18} /> : <ChevronDown className="text-slate-500" size={18} />}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="bg-slate-950 border-t border-slate-800 p-5 grid grid-cols-12 gap-8 animate-in slide-in-from-top-1 duration-150">
          
          {/* Left: Legs */}
          <div className="col-span-6 border-r border-slate-800 pr-6">
            <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Leg Structure</h4>
            <div className="space-y-1">
              {trade.legs.map((leg, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs font-mono p-2 bg-slate-900 rounded-[1px] border border-slate-800">
                  <div className="flex items-center space-x-3">
                    <span className={`px-1.5 py-0.5 text-[9px] uppercase font-bold rounded-[2px] ${leg.side === 'Long' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'}`}>
                      {leg.side}
                    </span>
                    <span className="text-slate-300 font-bold">{leg.strike} {leg.type}</span>
                  </div>
                  <span className="text-slate-500">Δ {leg.delta.toFixed(2)}</span>
                </div>
              ))}
            </div>
            
            <div className="mt-4 p-2 bg-slate-900/50 border border-slate-800 rounded-sm">
                <div className="flex items-center space-x-2 mb-1">
                    <Target size={12} className="text-indigo-400"/>
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Breakeven Points</span>
                </div>
                <span className="text-sm font-mono text-slate-200">
                    {trade.breakeven.map(b => b.toFixed(2)).join(' / ')}
                </span>
            </div>
          </div>

          {/* Right: Analytical Metrics - POST TRADE IMPACT */}
          <div className="col-span-6 space-y-4">
             <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold border-b border-slate-800 pb-2">Post-Trade Impact Analysis</h4>
             
             <div className="grid grid-cols-2 gap-3">
                 <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-slate-400">
                        <TrendingUp size={12} />
                        <span className="text-[10px] uppercase font-bold">Net Portfolio Delta</span>
                    </div>
                    <div className="flex items-center space-x-2">
                        <span className="text-sm font-mono text-slate-300">
                            {trade.postTradeImpact?.portfolioDelta && trade.postTradeImpact.portfolioDelta > 0 ? '+' : ''}
                            {trade.postTradeImpact?.portfolioDelta}
                        </span>
                        <span className="text-[10px] text-slate-600 font-mono">(Simulated)</span>
                    </div>
                 </div>

                 <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-slate-400">
                        <BarChart2 size={12} />
                        <span className="text-[10px] uppercase font-bold">Correlation Delta</span>
                    </div>
                    <div className="flex items-center space-x-2">
                        <span className={`text-sm font-mono ${trade.postTradeImpact?.correlationChange && trade.postTradeImpact.correlationChange > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {trade.postTradeImpact?.correlationChange && trade.postTradeImpact.correlationChange > 0 ? '+' : ''}
                            {trade.postTradeImpact?.correlationChange}
                        </span>
                    </div>
                 </div>

                 <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-slate-400">
                        <PieChart size={12} />
                        <span className="text-[10px] uppercase font-bold">Sector Exposure</span>
                    </div>
                    <div className="flex items-center space-x-2">
                        <span className="text-sm font-mono text-slate-300">
                             {trade.postTradeImpact?.sectorExposureChange && trade.postTradeImpact.sectorExposureChange > 0 ? '+' : ''}
                             {trade.postTradeImpact?.sectorExposureChange}%
                        </span>
                    </div>
                 </div>
             </div>

             <div className="flex justify-between items-center pt-4">
               <button className="flex-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white py-2 text-xs font-bold border border-slate-700 rounded-sm mr-2 transition-colors">
                  RUN MONTE CARLO
               </button>
               <button className="flex-1 bg-emerald-700 hover:bg-emerald-600 text-emerald-100 py-2 text-xs font-bold rounded-sm border border-emerald-600 shadow-lg shadow-emerald-900/20 transition-colors">
                  COMMIT TRADE
               </button>
             </div>
          </div>

        </div>
      )}
    </div>
  );
};
