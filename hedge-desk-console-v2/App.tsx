import React, { useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ScanView } from './components/ScanView';
import { PortfolioView } from './components/PortfolioView';
import { SettingsView } from './components/SettingsView';
import { DecisionLog } from './components/DecisionLog';
import { View } from './types';

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 flex flex-col">
      <Header />
      
      <div className="flex flex-1 max-w-[1920px] mx-auto w-full">
         <Sidebar currentView={currentView} onChangeView={setCurrentView} />
         
         <main className="flex-1 p-6 lg:p-8 overflow-y-auto h-[calc(100vh-72px)]">
            {currentView === 'dashboard' && <DashboardView onRunScan={() => setCurrentView('scan')} />}
            {currentView === 'scan' && <ScanView />}
            {currentView === 'portfolio' && <PortfolioView />}
            {currentView === 'settings' && <SettingsView />}
            {currentView === 'audit' && (
                <div className="max-w-3xl">
                    <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-4">System Decision Audit</h2>
                    <DecisionLog />
                </div>
            )}
         </main>
      </div>
    </div>
  );
}

export default App;
