import React from 'react';
import { PIPELINE_STAGES } from '../constants';
import { ChevronRight } from 'lucide-react';

export const PipelineBar: React.FC = () => {
  return (
    <div className="w-full bg-slate-900 border border-slate-700 p-1 mb-6 rounded-sm shadow-sm">
      <div className="flex items-center justify-between">
        {PIPELINE_STAGES.map((stage, index) => {
          const isLast = index === PIPELINE_STAGES.length - 1;
          
          let colorClass = 'text-slate-400 border-slate-700 bg-slate-800';
          let countClass = 'bg-slate-700 text-slate-300';

          if (stage.status === 'warning') {
            colorClass = 'text-amber-200 border-amber-900/50 bg-amber-900/10';
            countClass = 'bg-amber-900/50 text-amber-200';
          } else if (stage.status === 'success') {
            colorClass = 'text-emerald-200 border-emerald-900/50 bg-emerald-900/10';
            countClass = 'bg-emerald-900/50 text-emerald-200';
          } else if (stage.status === 'critical') {
             colorClass = 'text-rose-200 border-rose-900/50 bg-rose-900/10';
             countClass = 'bg-rose-900/50 text-rose-200';
          }

          return (
            <React.Fragment key={stage.id}>
              <div 
                className={`flex-1 flex items-center justify-between px-4 py-2 border rounded-sm transition-all hover:bg-opacity-20 cursor-pointer group ${colorClass}`}
              >
                <span className="text-xs font-bold uppercase tracking-wide group-hover:text-white transition-colors">
                  {stage.label}
                </span>
                <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-sm ${countClass}`}>
                  {stage.count}
                </span>
              </div>
              {!isLast && (
                <div className="px-1 text-slate-600">
                  <ChevronRight size={16} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
