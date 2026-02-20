import React from 'react';
import { View } from '../types';
import { LayoutDashboard, Radio, Briefcase, Settings, FileText } from 'lucide-react';

interface SidebarProps {
  currentView: View;
  onChangeView: (view: View) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onChangeView }) => {
  const NavItem = ({ view, icon: Icon, label }: { view: View; icon: any; label: string }) => {
    const isActive = currentView === view;
    return (
      <button
        onClick={() => onChangeView(view)}
        className={`w-full flex items-center space-x-3 px-4 py-3 mb-1 rounded-sm transition-all group ${
          isActive 
            ? 'bg-indigo-600/10 border-r-2 border-indigo-500 text-indigo-400' 
            : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
        }`}
      >
        <Icon size={18} className={isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'} />
        <span className="text-sm font-medium tracking-wide">{label}</span>
      </button>
    );
  };

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col pt-6 hidden lg:flex sticky top-[72px] h-[calc(100vh-72px)]">
      <div className="px-4 mb-6">
        <h3 className="text-[10px] uppercase text-slate-500 font-bold tracking-widest pl-2 mb-2">Modules</h3>
        <nav>
          <NavItem view="dashboard" icon={LayoutDashboard} label="Dashboard" />
          <NavItem view="scan" icon={Radio} label="Scan & Discovery" />
          <NavItem view="portfolio" icon={Briefcase} label="Portfolio & Risk" />
          <NavItem view="audit" icon={FileText} label="Decision Audit" />
        </nav>
      </div>

      <div className="px-4 mt-auto mb-6">
         <h3 className="text-[10px] uppercase text-slate-500 font-bold tracking-widest pl-2 mb-2">System</h3>
         <nav>
            <NavItem view="settings" icon={Settings} label="Settings / Lab" />
         </nav>
      </div>
    </aside>
  );
};
