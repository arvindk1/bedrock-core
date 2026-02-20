import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, CheckCircle, Terminal } from 'lucide-react';
import { PolicyMode } from '../types';

export const DecisionLog: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true); // Default open to be prominent

  return (
    <div className="mt-6 border border-slate-800 rounded-sm bg-slate-950">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-slate-900/50 text-slate-400 hover:text-slate-200 transition-colors"
      >
         <div className="flex items-center space-x-2">
            <Terminal size={14} />
            <span className="text-xs font-bold uppercase tracking-wider">Decision Logic Inspector</span>
         </div>
         {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {isOpen && (
        <div className="p-4 border-t border-slate-800 text-xs font-mono text-slate-400 space-y-3 max-h-64 overflow-y-auto">
          {/* Policy Snapshot */}
          <div className="flex items-center space-x-4 pb-3 border-b border-slate-800 mb-3 opacity-70">
              <span className="text-[10px] uppercase font-bold text-slate-500">Execution Snapshot:</span>
              <span>Policy: <span className="text-indigo-400">{PolicyMode.MODERATE}</span></span>
              <span>Risk/Trade: <span className="text-indigo-400">$2,500</span></span>
              <span>MinScore: <span className="text-indigo-400">85</span></span>
          </div>

          <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:01</span>
             <span className="text-emerald-500"><CheckCircle size={12} className="inline mr-1"/>Initialized Regime Scan: VOL_MED identified. Bias: Credit.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:05</span>
             <span>Loaded 250 option chains for universe [SPY, QQQ, IWM, ...].</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:15</span>
             <span className="text-indigo-400 font-bold">Pipeline Start:</span>
             <span>142 candidates generated based on Strategy:IronCondor.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:18</span>
             <span className="text-amber-500 font-bold">Risk Gate:</span>
             <span>Rejected 56 trades. Primary reason: Gamma Exposure > Limit.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:22</span>
             <span className="text-indigo-400 font-bold">Gatekeeper:</span>
             <span>Applied IV Rank threshold (>20%). 42 remaining.</span>
          </div>
           <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:30</span>
             <span className="text-indigo-400 font-bold">Correlation:</span>
             <span>Matrix check. 12 candidates passed diversity check.</span>
          </div>
           <div className="flex items-start space-x-3">
             <span className="text-slate-600 min-w-[60px]">10:00:35</span>
             <span className="text-emerald-500 font-bold">Final Selection:</span>
             <span>5 high-probability trades queued for review.</span>
          </div>
        </div>
      )}
    </div>
  );
};
