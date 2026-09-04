"use client";

import React, { useState, useCallback } from "react";
import Navbar from "../../components/Navbar";
import { useAuthSession } from "../../lib/auth";

// Domain & Governance Intelligence Components
import MLGovernanceTab from "../../components/MLGovernanceTab";
import FinOpsTab from "../../components/intelligence/FinOpsTab";
import ZeroTrustTab from "../../components/intelligence/ZeroTrustTab";
import ReleaseGovernanceTab from "../../components/intelligence/ReleaseGovernanceTab";
import PerformanceTab from "../../components/intelligence/PerformanceTab";
import DataGovernanceTab from "../../components/intelligence/DataGovernanceTab";
import ObservabilityTab from "../../components/intelligence/ObservabilityTab";
import ResilienceTab from "../../components/intelligence/ResilienceTab";
import ComplianceTab from "../../components/intelligence/ComplianceTab";
import SecurityTab from "../../components/intelligence/SecurityTab";
import ControlPlaneTab from "../../components/intelligence/ControlPlaneTab";

// ML & Strategy Intelligence Components (Phase 10J)
import ContinuousLearningTab from "../../components/intelligence/ContinuousLearningTab";
import ModelDeploymentTab from "../../components/intelligence/ModelDeploymentTab";
import ModelLifecycleTab from "../../components/intelligence/ModelLifecycleTab";
import ExperimentationTab from "../../components/intelligence/ExperimentationTab";
import ProductionMonitoringTab from "../../components/intelligence/ProductionMonitoringTab";
import StrategyActivationTab from "../../components/intelligence/StrategyActivationTab";
import StrategyGovernanceTab from "../../components/intelligence/StrategyGovernanceTab";
import CounterfactualSimulationTab from "../../components/intelligence/CounterfactualSimulationTab";
import StrategyOptimizationTab from "../../components/intelligence/StrategyOptimizationTab";
import ModelGovernanceSubTab from "../../components/intelligence/ModelGovernanceSubTab";
import IntelligenceEvaluationTab from "../../components/intelligence/IntelligenceEvaluationTab";

export type IntelligenceTab =
  | "ml_governance"
  | "finops"
  | "zero_trust"
  | "release_governance"
  | "performance"
  | "data_governance"
  | "observability"
  | "resilience"
  | "compliance"
  | "security"
  | "control_plane"
  | "learning"
  | "deployment"
  | "lifecycle"
  | "experimentation"
  | "production"
  | "rollout"
  | "recommendations"
  | "simulation"
  | "optimization"
  | "governance"
  | "evaluation";

export default function IntelligencePage() {
  const [activeTab, setActiveTab] = useState<IntelligenceTab>("ml_governance");
  const [refreshKey, setRefreshKey] = useState(0);
  const { session } = useAuthSession();
  const userRole = session.role;

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 antialiased">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800/80 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-tight text-white">
                Intelligence Control Plane &amp; Autonomous Governance
              </h1>
              <span className="rounded-full border border-emerald-500/60 bg-emerald-950/80 px-2.5 py-0.5 text-xs font-mono font-bold uppercase tracking-wider text-emerald-300">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              FinOps cost intelligence, zero-trust infrastructure, runtime threat correlation, 20 FinOps gates, and resource governance control plane.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* 22-Tab Selector */}
            <div className="flex flex-wrap items-center gap-1.5 rounded-xl bg-slate-900/90 p-1.5 border border-slate-800 backdrop-blur-md">
              <button
                onClick={() => setActiveTab("ml_governance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "ml_governance"
                    ? "bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-600 text-white shadow-lg shadow-cyan-500/40 font-black tracking-wide"
                    : "text-cyan-400 hover:text-cyan-200"
                }`}
              >
                🤖 ML Governance (10J)
              </button>
              <button
                onClick={() => setActiveTab("finops")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "finops"
                    ? "bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 text-white shadow-lg shadow-emerald-500/40 font-black tracking-wide"
                    : "text-emerald-400 hover:text-emerald-200"
                }`}
              >
                💰 FinOps &amp; Efficiency (10I)
              </button>
              <button
                onClick={() => setActiveTab("zero_trust")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "zero_trust"
                    ? "bg-gradient-to-r from-red-600 via-rose-600 to-orange-600 text-white shadow-lg shadow-red-500/40 font-black tracking-wide"
                    : "text-red-400 hover:text-red-200"
                }`}
              >
                🛡️ Zero-Trust Security (10H)
              </button>
              <button
                onClick={() => setActiveTab("release_governance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "release_governance"
                    ? "bg-gradient-to-r from-teal-600 via-emerald-600 to-cyan-600 text-white shadow-lg shadow-teal-500/40 font-black tracking-wide"
                    : "text-teal-400 hover:text-teal-200"
                }`}
              >
                🚀 Release Governance (10G)
              </button>
              <button
                onClick={() => setActiveTab("performance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "performance"
                    ? "bg-gradient-to-r from-indigo-600 via-blue-600 to-violet-600 text-white shadow-lg shadow-indigo-500/40 font-black tracking-wide"
                    : "text-indigo-400 hover:text-indigo-200"
                }`}
              >
                ⚡ Performance &amp; Capacity (10F)
              </button>
              <button
                onClick={() => setActiveTab("data_governance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "data_governance"
                    ? "bg-gradient-to-r from-cyan-600 via-teal-600 to-blue-600 text-white shadow-lg shadow-cyan-600/30 font-bold"
                    : "text-cyan-400 hover:text-cyan-200"
                }`}
              >
                Data Governance &amp; Privacy (10E)
              </button>
              <button
                onClick={() => setActiveTab("observability")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "observability"
                    ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30 font-bold"
                    : "text-blue-400 hover:text-blue-200"
                }`}
              >
                Observability &amp; SRE (10D)
              </button>
              <button
                onClick={() => setActiveTab("resilience")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "resilience"
                    ? "bg-gradient-to-r from-cyan-600 via-teal-600 to-indigo-600 text-white shadow-lg shadow-cyan-600/30 font-bold"
                    : "text-cyan-400 hover:text-cyan-200"
                }`}
              >
                Operational Resilience (10C)
              </button>
              <button
                onClick={() => setActiveTab("compliance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "compliance"
                    ? "bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-600 text-white shadow-lg shadow-teal-600/30 font-bold"
                    : "text-teal-400 hover:text-teal-200"
                }`}
              >
                Compliance &amp; Governance (10B)
              </button>
              <button
                onClick={() => setActiveTab("security")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "security"
                    ? "bg-gradient-to-r from-rose-600 via-pink-600 to-amber-600 text-white shadow-lg shadow-rose-600/30 font-bold"
                    : "text-rose-400 hover:text-rose-200"
                }`}
              >
                Security &amp; Trust (10A)
              </button>
              <button
                onClick={() => setActiveTab("control_plane")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "control_plane"
                    ? "bg-gradient-to-r from-amber-600 via-purple-600 to-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-bold"
                    : "text-amber-400 hover:text-amber-200"
                }`}
              >
                Control Plane (9L)
              </button>
              <button
                onClick={() => setActiveTab("learning")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "learning"
                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Continuous Learning
              </button>
              <button
                onClick={() => setActiveTab("deployment")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "deployment"
                    ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Model Deployment
              </button>
              <button
                onClick={() => setActiveTab("lifecycle")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "lifecycle"
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Model Lifecycle
              </button>
              <button
                onClick={() => setActiveTab("experimentation")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "experimentation"
                    ? "bg-purple-600 text-white shadow-lg shadow-purple-600/30 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Causal Experimentation
              </button>
              <button
                onClick={() => setActiveTab("production")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "production"
                    ? "bg-indigo-600 text-white shadow font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Production Intelligence
              </button>
              <button
                onClick={() => setActiveTab("rollout")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "rollout"
                    ? "bg-indigo-600 text-white shadow font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Controlled Rollout
              </button>
              <button
                onClick={() => setActiveTab("recommendations")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "recommendations"
                    ? "bg-indigo-600 text-white shadow font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Recommendations
              </button>
              <button
                onClick={() => setActiveTab("simulation")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "simulation"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Strategy Simulation
              </button>
              <button
                onClick={() => setActiveTab("optimization")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "optimization"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Strategy Optimization
              </button>
              <button
                onClick={() => setActiveTab("governance")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "governance"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Governance &amp; Drift
              </button>
              <button
                onClick={() => setActiveTab("evaluation")}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  activeTab === "evaluation"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Outcome Evaluation
              </button>
            </div>

            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-slate-700 hover:bg-slate-800 transition"
              title="Refresh intelligence state"
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Tab Views */}
        <div className="space-y-6">
          {activeTab === "ml_governance" && <MLGovernanceTab key={refreshKey} />}
          {activeTab === "finops" && <FinOpsTab key={refreshKey} />}
          {activeTab === "zero_trust" && <ZeroTrustTab key={refreshKey} />}
          {activeTab === "release_governance" && <ReleaseGovernanceTab key={refreshKey} />}
          {activeTab === "performance" && <PerformanceTab key={refreshKey} />}
          {activeTab === "data_governance" && <DataGovernanceTab key={refreshKey} />}
          {activeTab === "observability" && <ObservabilityTab key={refreshKey} />}
          {activeTab === "resilience" && <ResilienceTab key={refreshKey} />}
          {activeTab === "compliance" && <ComplianceTab key={refreshKey} />}
          {activeTab === "security" && <SecurityTab key={refreshKey} userRole={userRole} />}
          {activeTab === "control_plane" && (
            <ControlPlaneTab key={refreshKey} userRole={userRole} setActiveTab={(tab) => setActiveTab(tab as IntelligenceTab)} />
          )}
          {activeTab === "learning" && <ContinuousLearningTab key={refreshKey} userRole={userRole} />}
          {activeTab === "deployment" && <ModelDeploymentTab key={refreshKey} />}
          {activeTab === "lifecycle" && <ModelLifecycleTab key={refreshKey} userRole={userRole} />}
          {activeTab === "experimentation" && <ExperimentationTab key={refreshKey} userRole={userRole} />}
          {activeTab === "production" && <ProductionMonitoringTab key={refreshKey} userRole={userRole} />}
          {activeTab === "rollout" && <StrategyActivationTab key={refreshKey} userRole={userRole} />}
          {activeTab === "recommendations" && <StrategyGovernanceTab key={refreshKey} userRole={userRole} />}
          {activeTab === "simulation" && <CounterfactualSimulationTab key={refreshKey} />}
          {activeTab === "optimization" && <StrategyOptimizationTab key={refreshKey} />}
          {activeTab === "governance" && <ModelGovernanceSubTab key={refreshKey} />}
          {activeTab === "evaluation" && <IntelligenceEvaluationTab key={refreshKey} />}
        </div>
      </main>
    </div>
  );
}
