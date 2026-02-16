import React from 'react';
import { Settings, Sliders, PlayCircle } from 'lucide-react';
import { PolicyMode } from '../types';

export const StrategyControls: React.FC = () => {
  return (
    <div className="mt-6 bg-slate-900 border border-slate-700 p-4 rounded-sm shadow-sm">
      <div className="flex items-center space-x-2 mb-4 border-b border-slate-800 pb-2">
        <Settings size={16} className="text-slate-400" />
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wide">Strategy Parameters</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Policy Selector */}
        <div className="space-y-2">
          <label className="text-xs text-slate-500 uppercase font-bold">Execution Policy</label>
          <div className="relative">
            <select className="w-full bg-slate-950 text-slate-200 text-sm border border-slate-700 rounded-sm p-2 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none appearance-none font-mono">
              <option>{PolicyMode.TIGHT}</option>
              <option selected>{PolicyMode.MODERATE}</option>
              <option>{PolicyMode.AGGRESSIVE}</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
              <Sliders size={12} />
            </div>
          </div>
        </div>

        {/* Risk Input */}
        <div className="space-y-2">
          <label className="text-xs text-slate-500 uppercase font-bold">Max Risk / Trade ($)</label>
          <input 
            type="number" 
            defaultValue={2500} 
            className="w-full bg-slate-950 text-slate-200 text-sm border border-slate-700 rounded-sm p-2 font-mono focus:border-indigo-500 outline-none" 
          />
        </div>

        {/* Sliders */}
        <div className="space-y-3">
          <div className="flex justify-between text-xs text-slate-500 uppercase font-bold">
             <span>Min Gatekeeper Score</span>
             <span className="text-indigo-400">85</span>
          </div>
          <input type="range" className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500" />
        </div>

        {/* Toggles */}
        <div className="flex flex-col justify-center space-y-3">
           <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Allow Earnings Plays</span>
              <button className="w-10 h-5 rounded-full bg-slate-700 flex items-center transition-colors p-1 cursor-pointer">
                 <div className="w-3 h-3 bg-slate-400 rounded-full shadow-md transform transition-transform"></div>
              </button>
           </div>
           <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Regime Override</span>
               <button className="w-10 h-5 rounded-full bg-indigo-900 flex items-center transition-colors p-1 cursor-pointer justify-end">
                 <div className="w-3 h-3 bg-indigo-400 rounded-full shadow-md transform transition-transform"></div>
              </button>
           </div>
        </div>

      </div>
    </div>
  );
};
