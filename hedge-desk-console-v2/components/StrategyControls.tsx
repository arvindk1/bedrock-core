import React, { useState } from 'react';
import { Settings, Sliders, AlertTriangle } from 'lucide-react';
import { PolicyMode } from '../types';

export const StrategyControls: React.FC = () => {
  const [policy, setPolicy] = useState(PolicyMode.MODERATE);

  const isAggressive = policy === PolicyMode.AGGRESSIVE;

  return (
    <div className={`mt-6 bg-slate-900 border ${isAggressive ? 'border-amber-900/50' : 'border-slate-800'} p-5 rounded-sm shadow-sm transition-colors`}>
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
            <Settings size={16} className="text-slate-400" />
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide">Strategy Lab Controls</h3>
        </div>
        {isAggressive && (
            <div className="flex items-center space-x-2 text-amber-500 animate-pulse">
                <AlertTriangle size={14} />
                <span className="text-[10px] font-bold uppercase tracking-widest">High Risk Config</span>
            </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        
        {/* Policy Selector */}
        <div className="space-y-2">
          <label className="text-[10px] text-slate-500 uppercase font-bold">Execution Policy</label>
          <div className="relative">
            <select 
                value={policy}
                onChange={(e) => setPolicy(e.target.value as PolicyMode)}
                className="w-full bg-slate-950 text-slate-200 text-sm border border-slate-700 rounded-sm p-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none appearance-none font-mono"
            >
              <option>{PolicyMode.TIGHT}</option>
              <option>{PolicyMode.MODERATE}</option>
              <option>{PolicyMode.AGGRESSIVE}</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
              <Sliders size={12} />
            </div>
          </div>
        </div>

        {/* Risk Input */}
        <div className="space-y-2">
          <label className="text-[10px] text-slate-500 uppercase font-bold">Max Risk / Trade ($)</label>
          <input 
            type="number" 
            defaultValue={2500} 
            className="w-full bg-slate-950 text-slate-200 text-sm border border-slate-700 rounded-sm p-2 font-mono focus:border-indigo-500 outline-none placeholder-slate-700" 
          />
        </div>

        {/* Sliders */}
        <div className="space-y-4">
          <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-slate-500 uppercase font-bold">
                <span>Min Gatekeeper Score</span>
                <span className="text-indigo-400 font-mono">85</span>
              </div>
              <input type="range" min="0" max="100" defaultValue="85" className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500" />
          </div>
          
           <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-slate-500 uppercase font-bold">
                <span>Correlation Threshold</span>
                <span className="text-indigo-400 font-mono">0.65</span>
              </div>
              <input type="range" min="0" max="1" step="0.05" defaultValue="0.65" className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500" />
          </div>
        </div>

        {/* Toggles */}
        <div className="flex flex-col justify-center space-y-4 pl-4 border-l border-slate-800">
           <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Allow Earnings Plays</span>
              <button className="w-9 h-4 rounded-full bg-slate-700 flex items-center transition-colors p-0.5 cursor-pointer">
                 <div className="w-3 h-3 bg-slate-400 rounded-full shadow-md transform transition-transform"></div>
              </button>
           </div>
           <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Regime Override</span>
               <button className="w-9 h-4 rounded-full bg-indigo-900 flex items-center transition-colors p-0.5 cursor-pointer justify-end">
                 <div className="w-3 h-3 bg-indigo-400 rounded-full shadow-md transform transition-transform"></div>
              </button>
           </div>
        </div>

      </div>
    </div>
  );
};
