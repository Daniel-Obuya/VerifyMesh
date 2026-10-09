import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BrandLogo } from '../components/auth/BrandLogo';
import { Button } from '../components/ui/Button';
import { competencyService } from '../services/competencyService';

export const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [modelInfo, setModelInfo] = useState(null);

  useEffect(() => {
    const fetchInfo = async () => {
      try {
        const res = await competencyService.getModelInfo();
        if (res?.info) {
          setModelInfo(res.info);
        }
      } catch {
        // Fallback
      }
    };
    fetchInfo();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <BrandLogo size="sm" />
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold text-slate-800">{user?.fullName || 'System Administrator'}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
          </div>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
            Administrator
          </span>
          <Button variant="secondary" size="sm" onClick={handleLogout}>
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 sm:p-8 space-y-6">
        {/* Admin Header Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-xs">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Administration Console
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Oversee competency assessment integration, Google Colab model deployment, and role-based access
              </p>
            </div>
            <span className="px-3 py-1 text-xs font-medium rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
              Authenticated &bull; Role: Administrator
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-6">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Model Training Source
              </span>
              <p className="text-xl font-bold text-slate-900 mt-1.5">Google Colab</p>
              <p className="text-xs text-emerald-600 mt-0.5">External training &amp; tuning</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                VerifyMesh Application
              </span>
              <p className="text-xl font-bold text-slate-900 mt-1.5">Inference Only</p>
              <p className="text-xs text-blue-600 mt-0.5">Real-time prediction API active</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Active Model Artifact
              </span>
              <p className="text-xl font-bold text-slate-900 mt-1.5">
                {modelInfo?.model_file || 'tuned_random_forest.joblib'}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Preloaded on Flask startup</p>
            </div>
          </div>
        </div>

        {/* Architecture Info Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-xs">
          <h2 className="text-lg font-bold text-slate-900 mb-2">Decoupled ML Architecture</h2>
          <p className="text-xs sm:text-sm text-slate-600 mb-4 leading-relaxed">
            VerifyMesh strictly decouples model training from application execution. All training, hyperparameter optimization, and validation are performed in Google Colab notebooks.
          </p>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 font-mono text-xs text-slate-700 space-y-1">
            <p className="text-indigo-700 font-semibold mb-2 font-sans text-sm">VerifyMesh Operational Flow:</p>
            <p>1. Google Colab &rarr; Train, Tune, and Evaluate Random Forest</p>
            <p>2. Export Artifact &rarr; models/tuned_random_forest.joblib</p>
            <p>3. Flask Backend &rarr; Preloads model once at startup (src/inference.py)</p>
            <p>4. Agent Assessment &rarr; Real-time prediction (/api/competency/predict)</p>
            <p>5. Business Engine &rarr; Rules-based certification &amp; task eligibility check</p>
          </div>
        </div>
      </main>
    </div>
  );
};
