import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, CheckCircle } from 'lucide-react';

export const DecisionLog: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-4 border border-slate-800 rounded-sm bg-slate-950/50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-slate-500 hover:text-slate-300 hover:bg-slate-900 transition-colors"
      >
         <div className="flex items-center space-x-2">
            <FileText size={16} />
            <span className="text-xs font-bold uppercase tracking-wider">Decision Logic Inspector</span>
         </div>
         {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {isOpen && (
        <div className="p-4 border-t border-slate-800 text-xs font-mono text-slate-400 space-y-2 max-h-48 overflow-y-auto">
          <div className="flex items-start space-x-3">
             <span className="text-slate-600">10:00:01</span>
             <span className="text-emerald-500"><CheckCircle size={12} className="inline mr-1"/>Initialized Regime Scan: VOL_MED identified.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600">10:00:05</span>
             <span>Loaded 250 option chains for universe [SPY, QQQ, IWM, ...].</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600">10:00:15</span>
             <span className="text-indigo-400">Filter Pass 1:</span>
             <span>142 candidates generated based on Strategy:IronCondor.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600">10:00:18</span>
             <span className="text-amber-500">Risk Gate:</span>
             <span>Rejected 56 trades due to Gamma Exposure limits.</span>
          </div>
          <div className="flex items-start space-x-3">
             <span className="text-slate-600">10:00:22</span>
             <span className="text-indigo-400">Gatekeeper:</span>
             <span>Applied IV Rank threshold (>20%). 42 remaining.</span>
          </div>
        </div>
      )}
    </div>
  );
};
