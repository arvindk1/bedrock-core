import React from 'react';
import { Activity, AlertTriangle, TrendingUp, TrendingDown, Anchor } from 'lucide-react';
import { VolatilityRegime, PolicyMode } from '../types';

export const Header: React.FC = () => {
  return (
    <header className="bg-slate-900 border-b border-slate-700 px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-md">
      {/* Left: Symbol & Basic Data */}
      <div className="flex items-center space-x-8">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 p-1.5 rounded-sm">
            <Anchor size={18} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-indigo-100">HEDGE<span className="text-indigo-500">DESK</span></span>
        </div>

        <div className="h-8 w-px bg-slate-700 mx-2" />

        <div className="flex items-center space-x-4">
          <div className="flex flex-col">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Symbol</span>
            <div className="flex items-center space-x-2 cursor-pointer group">
              <span className="text-xl font-mono font-bold text-white group-hover:text-indigo-400 transition-colors">SPY</span>
              <span className="text-sm font-mono text-emerald-400">438.12</span>
            </div>
          </div>
          
          <div className="flex flex-col">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Vol Regime</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-yellow-500 border border-yellow-500/30">
              {VolatilityRegime.MED}
            </span>
          </div>

           <div className="flex flex-col">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">IV Rank</span>
            <span className="font-mono text-slate-200">24%</span>
          </div>

           <div className="flex flex-col">
            <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Trend</span>
             <div className="flex items-center space-x-1 text-emerald-500">
               <TrendingUp size={14} />
               <span className="text-xs font-bold">BULLISH</span>
             </div>
          </div>
        </div>
      </div>

      {/* Right: Policy & Alerts */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded-sm border border-slate-700">
            <Activity size={14} className="text-indigo-400" />
            <span className="text-xs text-slate-400 uppercase">Policy:</span>
            <span className="text-sm font-bold text-white">{PolicyMode.MODERATE}</span>
        </div>

        <div className="flex items-center space-x-4 border-l border-slate-700 pl-6">
          <div className="flex items-center space-x-2 text-amber-500 opacity-80 hover:opacity-100 cursor-pointer transition-opacity">
            <AlertTriangle size={16} />
            <span className="text-xs font-mono">CPI DATA IN 2D</span>
          </div>
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-xs text-emerald-500 font-mono">SYSTEM ONLINE</span>
        </div>
      </div>
    </header>
  );
};
