import React from 'react';
import { VolatilityRegime, PortfolioRisk } from '../types';
import { PORTFOLIO_RISK } from '../constants';
import { TrendingUp, Activity, ShieldAlert, BarChart2, ArrowRight } from 'lucide-react';
import { RiskDashboard } from './RiskDashboard';

interface DashboardViewProps {
  onRunScan: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onRunScan }) => {
  return (
    <div className="space-y-6">
      
      {/* Top Row: Regime & Snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        
        {/* Market Regime Card - The "Big Picture" */}
        <div className="md:col-span-8 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700 rounded-sm p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Activity size={120} />
            </div>
            
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                Market Regime Detected
            </h2>

            <div className="flex items-end space-x-6">
                <div>
                    <span className="text-5xl font-black text-white tracking-tighter">MED VOL</span>
                    <div className="text-amber-500 font-bold mt-1 text-sm tracking-wide">IV RANK: 24% • BIAS: NEUTRAL/SHORT PREM</div>
                </div>
                <div className="h-12 w-px bg-slate-700"></div>
                <div className="pb-1">
                    <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                        Implied volatility is elevated relative to realized movement. 
                        System recommends <strong>Iron Condors</strong> and <strong>Credit Spreads</strong> to capture premium decay.
                        Avoid debit strategies unless VIX &lt; 14.
                    </p>
                </div>
            </div>

            <div className="mt-8 flex items-center space-x-4">
                <button 
                    onClick={onRunScan}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 text-sm font-bold rounded-sm shadow-lg shadow-emerald-900/20 transition-all flex items-center space-x-2"
                >
                    <span>INITIATE DISCOVERY SCAN</span>
                    <ArrowRight size={16} />
                </button>
                <div className="text-xs text-slate-500 font-mono">
                    Last scan: 12 mins ago • 142 candidates found
                </div>
            </div>
        </div>

        {/* Portfolio Snapshot */}
        <div className="md:col-span-4 bg-slate-900 border border-slate-800 rounded-sm p-5 flex flex-col justify-between">
            <h3 className="text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Exposure Snapshot</h3>
            
            <div className="space-y-4">
                <div className="flex justify-between items-end">
                    <div className="flex items-center space-x-2 text-emerald-400">
                        <TrendingUp size={18} />
                        <span className="text-lg font-mono font-bold">+{PORTFOLIO_RISK.netDelta}</span>
                    </div>
                    <span className="text-[10px] text-slate-500 uppercase">Net Portfolio Delta</span>
                </div>

                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full w-[60%]"></div>
                </div>

                <div className="flex justify-between items-end pt-2 border-t border-slate-800">
                    <div className="flex items-center space-x-2 text-amber-500">
                        <ShieldAlert size={18} />
                        <span className="text-lg font-mono font-bold">{PORTFOLIO_RISK.dailyDrawdown}%</span>
                    </div>
                    <span className="text-[10px] text-slate-500 uppercase">Daily Drawdown</span>
                </div>
            </div>
        </div>
      </div>

      {/* Bottom Row: Recent Decisions & Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-sm p-1">
             <div className="p-3 border-b border-slate-800 flex justify-between items-center">
                 <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest">Risk Visualization</h3>
                 <BarChart2 size={14} className="text-slate-500" />
             </div>
             {/* CHANGED: Removed fixed height, let it expand */}
             <div className="p-2 min-h-[300px]">
                 <RiskDashboard />
             </div>
          </div>
          
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-sm p-4">
               <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-4">Live Feed</h3>
               <div className="space-y-3">
                   {[1,2,3].map(i => (
                       <div key={i} className="flex items-start space-x-3 text-xs border-b border-slate-800/50 pb-2 last:border-0">
                           <span className="text-slate-500 font-mono">10:0{i}:24</span>
                           <div>
                               <span className="block text-slate-300">New candidate detected: <span className="text-indigo-400 font-bold">NVDA</span></span>
                               <span className="text-slate-600">Passed Gatekeeper (Score: 88)</span>
                           </div>
                       </div>
                   ))}
               </div>
          </div>
      </div>
    </div>
  );
};
