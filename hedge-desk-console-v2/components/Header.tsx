import React from 'react';
import { Activity, AlertTriangle, TrendingUp, Anchor, Info } from 'lucide-react';
import { VolatilityRegime, PolicyMode } from '../types';

export const Header: React.FC = () => {
  return (
    <header className="bg-slate-950 border-b border-slate-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-2xl shadow-black/50">
      {/* Left: Branding & Symbol */}
      <div className="flex items-center space-x-8">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 p-1.5 rounded-sm shadow-lg shadow-indigo-500/20">
            <Anchor size={20} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-indigo-100">HEDGE<span className="text-indigo-500">DESK</span></span>
        </div>

        <div className="h-10 w-px bg-slate-800 mx-2" />

        {/* DOMINANT REGIME DISPLAY */}
        <div className="flex items-center space-x-4 bg-slate-900/50 p-2 rounded-sm border border-slate-800/50">
           <div className="flex flex-col items-start px-2">
             <div className="flex items-center space-x-2">
               <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Market Regime</span>
               <Info size={10} className="text-slate-600 hover:text-slate-400 cursor-help" />
             </div>
             <div className="flex items-center space-x-3 mt-0.5">
                <span className="text-2xl font-black text-amber-500 tracking-tight">MED VOL</span>
                <span className="text-xs font-mono text-slate-400 border-l border-slate-700 pl-3">
                   Bias: <span className="text-indigo-400 font-bold">Credit Spreads</span>
                </span>
             </div>
           </div>
        </div>
      </div>

      {/* Middle: Quick Metrics */}
      <div className="flex items-center space-x-6">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Symbol</span>
            <div className="flex items-center space-x-2 group cursor-pointer">
              <span className="text-lg font-mono font-bold text-white group-hover:text-indigo-400 transition-colors">SPX</span>
              <span className="text-xs font-mono text-emerald-400">4385.12</span>
            </div>
          </div>
          
           <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">IV Rank</span>
            <span className="font-mono text-sm text-slate-200 font-bold">24%</span>
          </div>

           <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Trend</span>
             <div className="flex items-center space-x-1 text-emerald-500">
               <TrendingUp size={14} />
               <span className="text-xs font-bold">BULLISH</span>
             </div>
          </div>
      </div>

      {/* Right: Policy & Alerts */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2 bg-slate-900 px-4 py-2 rounded-sm border border-slate-800">
            <Activity size={14} className="text-indigo-400" />
            <span className="text-[10px] text-slate-400 uppercase font-bold">Policy:</span>
            <span className="text-sm font-bold text-white">{PolicyMode.MODERATE}</span>
        </div>

        <div className="flex items-center space-x-4 border-l border-slate-800 pl-6">
          <div className="flex items-center space-x-2 text-amber-500 opacity-80 hover:opacity-100 cursor-pointer transition-opacity">
            <AlertTriangle size={16} />
            <span className="text-[10px] font-mono font-bold">CPI: 2D</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-[10px] text-emerald-500 font-mono font-bold">LIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
};
