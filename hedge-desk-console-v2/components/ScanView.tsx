import React, { useState } from 'react';
import { VerticalPipeline } from './VerticalPipeline';
import { TradeTable } from './TradeTable';
import { StageInspector } from './StageInspector';
import { MOCK_TRADES } from '../constants';
import { Search, Sliders } from 'lucide-react';

export const ScanView: React.FC = () => {
  const [selectedStage, setSelectedStage] = useState('final');

  return (
    <div className="h-full flex flex-col">
       {/* Top Controls */}
       <div className="bg-slate-900 border border-slate-800 p-3 rounded-sm mb-4 flex items-center justify-between">
           <div className="flex items-center space-x-4">
                <div className="relative">
                    <Search className="absolute left-3 top-2.5 text-slate-500" size={14} />
                    <input type="text" placeholder="Filter Universe..." className="bg-slate-950 border border-slate-700 rounded-sm pl-9 pr-4 py-1.5 text-sm text-white focus:border-indigo-500 outline-none w-64" />
                </div>
                <select className="bg-slate-950 border border-slate-700 text-slate-300 text-sm py-1.5 px-3 rounded-sm outline-none">
                    <option>Exp: 30-45 DTE</option>
                    <option>Exp: 0-7 DTE (Weekly)</option>
                    <option>Exp: 60+ DTE</option>
                </select>
           </div>
           
           <button className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase hover:text-white transition-colors">
               <Sliders size={14} />
               <span>Scan Config</span>
           </button>
       </div>

       <div className="grid grid-cols-12 gap-6 flex-grow items-start">
           {/* Left: Gate Funnel */}
           <div className="col-span-3">
               <h3 className="text-[10px] uppercase text-slate-500 font-bold tracking-widest mb-3 pl-1">Filtering Pipeline</h3>
               <VerticalPipeline selectedStageId={selectedStage} onSelectStage={setSelectedStage} />
           </div>

           {/* Right: Output */}
           <div className="col-span-9 h-full">
               <div className="flex items-center justify-between mb-3">
                   <h3 className="text-[10px] uppercase text-slate-500 font-bold tracking-widest flex items-center gap-2">
                       {selectedStage === 'final' ? 'Actionable Candidates' : 'Stage Inspection'}
                   </h3>
                   {selectedStage === 'final' && <span className="text-[10px] text-emerald-500 font-mono">3 High Probability Trades</span>}
               </div>
               
               {selectedStage === 'final' ? (
                   <TradeTable trades={MOCK_TRADES} />
               ) : (
                   <StageInspector stageId={selectedStage} />
               )}
           </div>
       </div>
    </div>
  );
};
