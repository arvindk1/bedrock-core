import React from 'react';
import { Header } from './components/Header';
import { PipelineBar } from './components/PipelineBar';
import { TradeCard } from './components/TradeCard';
import { RejectionPanel } from './components/RejectionPanel';
import { RiskDashboard } from './components/RiskDashboard';
import { StrategyControls } from './components/StrategyControls';
import { DecisionLog } from './components/DecisionLog';
import { MOCK_TRADES } from './constants';

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30">
      <Header />
      
      <main className="p-6 max-w-[1600px] mx-auto">
        <PipelineBar />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Trade Output (70%) */}
          <div className="lg:col-span-8 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-widest flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                Final Picks
              </h2>
              <span className="text-xs text-slate-500 font-mono">Last updated: 10:05:00</span>
            </div>
            
            <div className="space-y-2">
              {MOCK_TRADES.map(trade => (
                <TradeCard key={trade.id} trade={trade} />
              ))}
            </div>

            <RejectionPanel />
          </div>

          {/* Right Column: Risk & Analytics (30%) */}
          <div className="lg:col-span-4 flex flex-col">
             <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-widest">Portfolio Risk</h2>
            </div>
            <div className="flex-grow">
               <RiskDashboard />
            </div>
          </div>
        </div>

        <StrategyControls />
        <DecisionLog />

      </main>
      
      {/* Footer / Status Bar */}
      <footer className="mt-12 py-4 border-t border-slate-800 text-center">
        <p className="text-[10px] text-slate-600 uppercase font-mono tracking-widest">
           Hedge Desk Console v2.4.0 • Connected to FIX Gateway • Latency: 12ms
        </p>
      </footer>
    </div>
  );
}

export default App;
