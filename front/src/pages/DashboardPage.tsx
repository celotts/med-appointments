import React from 'react';
import { Users, Calendar, CheckCircle, AlertCircle } from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, color }: any) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
    <div className={`p-3 rounded-xl ${color} text-white`}>
      <Icon size={24} />
    </div>
    <div>
      <p className="text-sm text-medical-textMuted font-medium">{title}</p>
      <h3 className="text-2xl font-bold text-medical-textMain">{value}</h3>
    </div>
  </div>
);

const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-medical-textMain">Clinical Overview</h2>
        <p className="text-medical-textMuted">Welcome back! Here is what's happening today.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Patients"
          value="1,284"
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          title="Appointments Today"
          value="12"
          icon={Calendar}
          color="bg-indigo-500"
        />
        <StatCard
          title="Completed"
          value="8"
          icon={CheckCircle}
          color="bg-emerald-500"
        />
        <StatCard
          title="Pending"
          value="4"
          icon={AlertCircle}
          color="bg-amber-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-lg transition-colors">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 bg-slate-100 rounded-full flex items-center justify-center text-xs font-bold">P{i}</div>
                  <div>
                    <p className="text-sm font-medium">Patient Appointment #{100 + i}</p>
                    <p className="text-xs text-medical-textMuted">Scheduled for 10:30 AM</p>
                  </div>
                </div>
                <span className="text-xs px-2 py-1 bg-blue-100 text-blue-600 rounded-full font-medium">Confirmed</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold mb-4">AI Assistant Insights</h3>
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
            <p className="text-sm text-blue-800 leading-relaxed">
              "Based on historical patterns, you have a 15% higher no-show rate on Friday afternoons. Consider sending extra reminders for tomorrow's appointments."
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
