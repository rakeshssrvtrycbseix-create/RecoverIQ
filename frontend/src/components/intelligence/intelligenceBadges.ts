// Intelligence Badge and Color Helpers

export const getGlobalStateBadge = (state?: string) => {
    switch (state) {
      case "SECURE":
        return "bg-emerald-950/90 border-emerald-500/80 text-emerald-300 font-extrabold shadow-[0_0_12px_rgba(16,185,129,0.3)]";
      case "MONITORING":
      case "INVESTIGATION_REQUIRED":
        return "bg-cyan-950/90 border-cyan-500/80 text-cyan-300 font-bold";
      case "SECURITY_DEGRADED":
      case "THREAT_DETECTED":
        return "bg-amber-950/90 border-amber-500/80 text-amber-300 font-bold animate-pulse";
      case "HIGH_SECURITY_RISK":
      case "TRUST_BOUNDARY_VIOLATION":
        return "bg-orange-950/90 border-orange-500/80 text-orange-300 font-extrabold animate-pulse";
      case "ACTIVE_ATTACK":
      case "CRITICAL_SECURITY_BREACH":
      case "EMERGENCY_SECURITY_LOCKDOWN":
        return "bg-red-950/90 border-red-500/90 text-red-200 font-black tracking-widest animate-bounce shadow-[0_0_20px_rgba(239,68,68,0.5)]";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getZtScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400 border-emerald-500/50 bg-emerald-950/40";
    if (score >= 80) return "text-cyan-400 border-cyan-500/50 bg-cyan-950/40";
    if (score >= 70) return "text-amber-400 border-amber-500/50 bg-amber-950/40";
    if (score >= 60) return "text-orange-400 border-orange-500/50 bg-orange-950/40";
    return "text-red-400 border-red-500/50 bg-red-950/40";
  };


export const getThreatSeverityBadge = (severity: string) => {
    switch (severity) {
      case "LOW":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-medium";
      case "MEDIUM":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
      case "HIGH":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-extrabold";
      case "CRITICAL":
        return "bg-red-950/90 border-red-600/80 text-red-300 font-black animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.4)]";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getSecurityControlBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "BYPASS_PREVENTED":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-black tracking-wider";
      case "DEGRADED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold animate-pulse";
      case "DISABLED":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getSecurityThreatLevelBadge = (level: string) => {
    switch (level) {
      case "CRITICAL":
        return "bg-red-950/90 border-red-500 text-red-200 font-black animate-pulse";
      case "ELEVATED":
        return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
      case "NOMINAL":
      default:
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
    }
  };


export const getCompliancePostureBadge = (posture?: string) => {
    switch (posture) {
      case "EXCELLENT":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-200 font-black";
      case "GOOD":
        return "bg-teal-950/90 border-teal-500 text-teal-200 font-bold";
      case "WARNING":
        return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
      case "HIGH_RISK":
        return "bg-orange-950/90 border-orange-500 text-orange-200 font-bold animate-pulse";
      case "CRITICAL":
        return "bg-rose-950/90 border-rose-500 text-rose-200 font-black animate-pulse";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getComplianceControlStatusBadge = (status: string) => {
    switch (status) {
      case "PASS":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "WARNING":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
      case "FAIL":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-black";
      case "NOT_ASSESSED":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getComplianceSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-red-950/90 border-red-500 text-red-200 font-black animate-pulse";
      case "HIGH":
        return "bg-rose-950/90 border-rose-500 text-rose-200 font-bold";
      case "MEDIUM":
        return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
      case "LOW":
      default:
        return "bg-blue-950/90 border-blue-500 text-blue-200 font-medium";
    }
  };


export const getActivationStatusBadge = (status: string) => {
    switch (status) {
      case "CANARY":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 animate-pulse";
      case "ACTIVE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "APPROVED":
        return "bg-blue-950/80 border-blue-700/60 text-blue-300";
      case "PAUSED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      case "ROLLED_BACK":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "EXPIRED":
        return "bg-slate-900 border-slate-700 text-slate-500";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getRolloutHealthBadge = (status: string) => {
    switch (status) {
      case "SAFE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "WARNING":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      case "ROLLBACK_RECOMMENDED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 animate-pulse font-bold";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getProductionStatusBadge = (status: string) => {
    switch (status) {
      case "HEALTHY":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "WARNING":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      case "DEGRADED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "ROLLBACK_RECOMMENDED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 animate-pulse font-bold";
      case "NO_ACTIVE_STRATEGY":
        return "bg-slate-900 border-slate-700 text-slate-400";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getStatusBadge = (status: string) => {
    switch (status) {
      case "HEALTHY":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "WARNING":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      case "DEGRADED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getRecommendationStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "REJECTED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "REVIEW_REQUIRED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 animate-pulse";
      case "EXPIRED":
        return "bg-slate-900 border-slate-700 text-slate-500";
      case "OBSERVATIONAL":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getConfidenceLevelBadge = (level: string) => {
    switch (level) {
      case "HIGH":
        return "bg-emerald-950/60 border-emerald-800/40 text-emerald-300";
      case "MEDIUM":
        return "bg-amber-950/60 border-amber-800/40 text-amber-300";
      case "LOW":
        return "bg-rose-950/60 border-rose-800/40 text-rose-300";
      default:
        return "bg-slate-900 border-slate-800 text-slate-400";
    }
  };


export const getReliabilityBadge = (rel: string) => {
    switch (rel) {
      case "SUFFICIENT":
        return "bg-emerald-950/60 border-emerald-800/40 text-emerald-300";
      case "LIMITED":
        return "bg-amber-950/60 border-amber-800/40 text-amber-300";
      default:
        return "bg-slate-900 border-slate-800 text-slate-400";
    }
  };


export const getAssessmentBadge = (assessment: string) => {
    switch (assessment) {
      case "STRONG_POSITIVE_EVIDENCE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300";
      case "MODERATE_EVIDENCE":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300";
      case "NEGATIVE_OUTCOME_INDICATED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "COMPARABLE_PERFORMANCE":
        return "bg-indigo-950/80 border-indigo-700/60 text-indigo-300";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getDriftBadge = (level: string) => {
    switch (level) {
      case "LOW":
        return "bg-emerald-950/60 border-emerald-800/40 text-emerald-400";
      case "MODERATE":
        return "bg-amber-950/60 border-amber-800/40 text-amber-400";
      case "SIGNIFICANT":
        return "bg-rose-950/60 border-rose-800/40 text-rose-400";
      default:
        return "bg-slate-900 border-slate-800 text-slate-400";
    }
  };


export const getExperimentStatusBadge = (status: string) => {
    switch (status) {
      case "RUNNING":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 animate-pulse font-bold";
      case "DRAFT":
        return "bg-slate-900 border-slate-700 text-slate-400";
      case "PAUSED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
      case "COMPLETED":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-bold";
      case "STOPPED":
      case "CANCELLED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getEvidenceBadge = (level: string) => {
    switch (level) {
      case "LEVEL_3":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "LEVEL_2":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
      case "LEVEL_1":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      case "LEVEL_0":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case "PROMOTE_TO_REVIEW":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "STOP_RECOMMENDED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 animate-pulse font-bold";
      case "CONTINUE":
        return "bg-indigo-950/80 border-indigo-700/60 text-indigo-300 font-bold";
      case "INSUFFICIENT_DATA":
      default:
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
    }
  };


export const getModelLifecycleBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "PROMOTION_READY":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-bold";
      case "REVIEW_REQUIRED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold animate-pulse";
      case "APPROVED":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
      case "TRAINING":
      case "VALIDATING":
        return "bg-indigo-950/80 border-indigo-700/60 text-indigo-300 animate-pulse";
      case "REJECTED":
      case "FAILED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
      case "RETIRED":
      case "DRAFT":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getModelRecommendationBadge = (rec: string) => {
    switch (rec) {
      case "PROMOTE_CHALLENGER_REVIEW":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "KEEP_CHAMPION":
        return "bg-indigo-950/80 border-indigo-700/60 text-indigo-300 font-bold";
      case "REJECT_CHALLENGER":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
      case "INSUFFICIENT_DATA":
      default:
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
    }
  };


export const getComparisonDeltaBadge = (status: string) => {
    switch (status) {
      case "IMPROVED":
        return "bg-emerald-950/60 border-emerald-800/40 text-emerald-400 font-bold";
      case "REGRESSED":
        return "bg-rose-950/60 border-rose-800/40 text-rose-400 font-bold";
      case "UNCHANGED":
      default:
        return "bg-slate-900 border-slate-800 text-slate-400";
    }
  };


export const getBalanceBadge = (status: string) => {
    switch (status) {
      case "BALANCED":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "MINOR_IMBALANCE":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
      case "MAJOR_IMBALANCE":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getDeploymentStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "CANARY":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-bold animate-pulse";
      case "SHADOW":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
      case "PAUSED":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
      case "ROLLBACK_REQUIRED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold animate-bounce";
      case "RETIRED":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getDeploymentReadinessDecisionBadge = (decision: string) => {
    switch (decision) {
      case "PROMOTION_READY":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "CANARY_ELIGIBLE":
        return "bg-purple-950/80 border-purple-700/60 text-purple-300 font-bold";
      case "CONTINUE_SHADOW":
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300 font-bold";
      case "ROLLBACK_RECOMMENDED":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
      case "INSUFFICIENT_DATA":
      case "HOLD":
      default:
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
    }
  };


export const getDeploymentSignificanceBadge = (sig: string) => {
    switch (sig) {
      case "STATISTICALLY_SIGNIFICANT":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "NOT_STATISTICALLY_SIGNIFICANT":
        return "bg-slate-900 border-slate-700 text-slate-400 font-bold";
      case "INSUFFICIENT_DATA":
      default:
        return "bg-amber-950/80 border-amber-700/60 text-amber-300 font-bold";
    }
  };


export const getEvolutionDecisionBadge = (decision: string) => {
    switch (decision) {
      case "RETRAIN_RECOMMENDED":
        return "bg-indigo-950/90 border-indigo-500 text-indigo-300 font-bold animate-pulse shadow-lg shadow-indigo-500/20";
      case "CHALLENGER_READY":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
      case "REVIEW_REQUIRED":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold animate-pulse";
      case "PROMOTION_BLOCKED":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold";
      case "RETIRE_RECOMMENDED":
        return "bg-purple-950/90 border-purple-500 text-purple-300 font-bold";
      case "NO_ACTION":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getEligibilityDecisionBadge = (decision: string) => {
    switch (decision) {
      case "ELIGIBLE":
      case "DRIFT_TRIGGERED":
      case "PERFORMANCE_TRIGGERED":
      case "CALIBRATION_TRIGGERED":
        return "bg-emerald-950/80 border-emerald-700/60 text-emerald-300 font-bold";
      case "WAITING_FOR_DATA":
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
      case "BLOCKED_BY_DATA_QUALITY":
      case "BLOCKED_BY_ACTIVE_TRAINING":
      default:
        return "bg-rose-950/80 border-rose-700/60 text-rose-300 font-bold";
    }
  };


export const getSubsystemStatusBadge = (status?: string) => {
    switch (status) {
      case "CRITICAL":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold";
      case "DEGRADED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "WARNING":
        return "bg-yellow-950/80 border-yellow-600 text-yellow-300 font-bold";
      case "HEALTHY":
      default:
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-medium";
    }
  };


export const getIncidentSeverityBadge = (sev?: string) => {
    switch (sev) {
      case "CRITICAL":
        return "bg-red-950/90 border-red-500 text-red-200 font-black";
      case "HIGH":
        return "bg-rose-950/90 border-rose-500 text-rose-200 font-bold";
      case "MEDIUM":
        return "bg-amber-950/90 border-amber-500 text-amber-200 font-bold";
      case "LOW":
      default:
        return "bg-blue-950/90 border-blue-500 text-blue-200 font-medium";
    }
  };


export const getResilienceStateBadge = (state?: string) => {
    switch (state) {
      case "DISASTER_MODE":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      case "CRITICAL":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse shadow-lg shadow-rose-500/20";
      case "SERVICE_IMPACTED":
        return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
      case "DEGRADED":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "WARNING":
        return "bg-yellow-950/90 border-yellow-500 text-yellow-300 font-bold";
      case "RECOVERY_IN_PROGRESS":
        return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-bold animate-pulse";
      case "RECOVERY_VERIFIED":
        return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
      case "OPERATIONAL":
      default:
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
    }
  };


export const getServiceHealthBadge = (status?: string) => {
    switch (status) {
      case "HEALTHY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "DEGRADED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "UNAVAILABLE":
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
      case "UNKNOWN":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getReadinessGateBadge = (status?: string) => {
    switch (status) {
      case "READY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "CONDITIONAL":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "BLOCKED":
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
      case "UNKNOWN":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getRTORPOBadge = (status?: string) => {
    switch (status) {
      case "COMPLIANT":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "AT_RISK":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "BREACHED":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
      case "UNKNOWN":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getGovernanceScoreBadge = (classification?: string) => {
    switch (classification) {
      case "EXCELLENT":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
      case "GOOD":
        return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
      case "WARNING":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "HIGH_RISK":
        return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
    }
  };


export const getDataQualityBadge = (status?: string) => {
    switch (status) {
      case "HEALTHY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "DEGRADED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getDataClassificationBadge = (classification?: string) => {
    switch (classification) {
      case "FINANCIAL_RESTRICTED":
        return "bg-purple-950/90 border-purple-500 text-purple-300 font-black";
      case "RESTRICTED":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold";
      case "SENSITIVE":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-medium";
      case "CONFIDENTIAL":
        return "bg-blue-950/90 border-blue-500 text-blue-300 font-medium";
      case "INTERNAL":
        return "bg-slate-900 border-slate-700 text-slate-300 font-medium";
      case "PUBLIC":
      default:
        return "bg-slate-950 border-slate-800 text-slate-400 font-medium";
    }
  };


export const getPrivacyControlBadge = (status?: string) => {
    switch (status) {
      case "PASS":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "WARNING":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "FAIL":
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
      case "NOT_APPLICABLE":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getRetentionStatusBadge = (status?: string) => {
    switch (status) {
      case "WITHIN_POLICY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "EXPIRING_SOON":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "OVERDUE":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
      case "LEGAL_HOLD":
        return "bg-purple-950/80 border-purple-600 text-purple-300 font-bold";
      case "EXEMPT":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getPrivacyRequestBadge = (status?: string) => {
    switch (status) {
      case "RECEIVED":
        return "bg-blue-950/80 border-blue-600 text-blue-300 font-bold";
      case "UNDER_REVIEW":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "APPROVED":
        return "bg-indigo-950/80 border-indigo-600 text-indigo-300 font-bold";
      case "REJECTED":
        return "bg-rose-950/80 border-rose-600 text-rose-300 font-bold";
      case "COMPLETED":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "BLOCKED":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getPrivacySeverityBadge = (severity?: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      case "HIGH":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold";
      case "MEDIUM":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-medium";
      case "LOW":
      default:
        return "bg-slate-900 border-slate-700 text-slate-300 font-medium";
    }
  };


export const getOperationalStateBadge = (state?: string) => {
    switch (state) {
      case "EMERGENCY_OPERATIONAL_STATE":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      case "CRITICAL_INCIDENT":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse shadow-lg shadow-rose-500/20";
      case "MAJOR_INCIDENT":
        return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
      case "INCIDENT":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "DEGRADED":
        return "bg-yellow-950/90 border-yellow-500 text-yellow-300 font-bold";
      case "WARNING":
        return "bg-yellow-950/80 border-yellow-600 text-yellow-300 font-medium";
      case "MONITORING":
        return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-medium";
      case "RECOVERY":
        return "bg-indigo-950/90 border-indigo-500 text-indigo-300 font-bold";
      case "STABILIZED":
        return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
      case "HEALTHY":
      default:
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
    }
  };


export const getSLOStatusBadge = (status?: string) => {
    switch (status) {
      case "COMPLIANT":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "AT_RISK":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "BREACHED":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold animate-pulse";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getSRESeverityBadge = (sev?: string) => {
    switch (sev) {
      case "SEV_1":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      case "SEV_2":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse";
      case "SEV_3":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "SEV_4":
      default:
        return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-medium";
    }
  };


export const getTraceStatusBadge = (status?: string) => {
    switch (status) {
      case "OK":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "DEGRADED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "ERROR":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold";
      default:
        return "bg-slate-900 border-slate-700 text-slate-400 font-medium";
    }
  };


export const getPerformanceScoreBadge = (classification?: string) => {
    switch (classification) {
      case "EXCELLENT":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
      case "GOOD":
        return "bg-teal-950/90 border-teal-500 text-teal-300 font-bold";
      case "WARNING":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "DEGRADED":
        return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
    }
  };


export const getPerformanceGlobalStateBadge = (state?: string) => {
    switch (state) {
      case "EMERGENCY_CAPACITY_FAILURE":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse shadow-lg shadow-red-500/20";
      case "PERFORMANCE_CRITICAL":
        return "bg-rose-950/90 border-rose-500 text-rose-300 font-bold animate-pulse";
      case "CAPACITY_EXHAUSTION":
        return "bg-orange-950/90 border-orange-500 text-orange-300 font-bold";
      case "SEVERE_DEGRADATION":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "PERFORMANCE_DEGRADED":
        return "bg-yellow-950/90 border-yellow-500 text-yellow-300 font-medium";
      case "HIGH_UTILIZATION":
        return "bg-indigo-950/90 border-indigo-500 text-indigo-300 font-medium";
      case "SCALING_RECOMMENDED":
        return "bg-purple-950/90 border-purple-500 text-purple-300 font-bold";
      case "PERFORMANCE_WARNING":
        return "bg-blue-950/90 border-blue-500 text-blue-300 font-medium";
      case "MONITORING":
        return "bg-cyan-950/90 border-cyan-500 text-cyan-300 font-medium";
      case "HEALTHY":
      default:
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/20";
    }
  };


export const getQueueStateBadge = (state?: string) => {
    switch (state) {
      case "QUEUE_HEALTHY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "QUEUE_GROWING":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "QUEUE_SATURATED":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "QUEUE_CRITICAL":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getDbPerformanceStateBadge = (state?: string) => {
    switch (state) {
      case "DB_HEALTHY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "DB_WARNING":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "DB_DEGRADED":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "DB_SATURATED":
      case "DB_CRITICAL":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getCachePerformanceStateBadge = (state?: string) => {
    switch (state) {
      case "CACHE_HEALTHY":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "CACHE_WARNING":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "CACHE_DEGRADED":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "CACHE_PRESSURED":
      case "CACHE_CRITICAL":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getPerformanceGateBadge = (status?: string) => {
    switch (status) {
      case "PASS":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "WARN":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "FAIL":
      default:
        return "bg-red-950/80 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getReleaseHealthBadge = (health?: string) => {
    switch (health) {
      case "EXCELLENT":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-black shadow-lg shadow-emerald-500/20";
      case "HEALTHY":
        return "bg-teal-950/80 border-teal-500 text-teal-300 font-bold";
      case "WARNING":
        return "bg-amber-950/80 border-amber-500 text-amber-300 font-bold";
      case "DEGRADED":
        return "bg-orange-950/80 border-orange-500 text-orange-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/90 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getReleaseDecisionBadge = (decision?: string) => {
    switch (decision) {
      case "GO":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-black shadow-lg shadow-emerald-500/20";
      case "CONDITIONAL_GO":
        return "bg-amber-950/90 border-amber-500 text-amber-300 font-bold";
      case "NO_GO":
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse";
      case "PENDING_REVIEW":
      default:
        return "bg-blue-950/80 border-blue-600 text-blue-300 font-semibold";
    }
  };


export const getChangeRiskBadge = (risk?: string) => {
    switch (risk) {
      case "LOW":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "MEDIUM":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "HIGH":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/90 border-red-500 text-red-300 font-black animate-pulse";
    }
  };


export const getZtScoreBadge = (status?: string) => {
    switch (status) {
      case "TRUSTED":
      case "OPTIMAL":
      case "LOW":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "ACCEPTABLE":
      case "DEGRADED":
      case "ELEVATED":
      case "MEDIUM":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "CRITICAL":
      case "HIGH_RISK":
      case "HIGH":
      default:
        return "bg-rose-950/80 border-rose-600 text-rose-300 font-bold";
    }
  };


export const getChangeStatusBadge = (status?: string) => {
    switch (status) {
      case "PROPOSED":
        return "bg-slate-900 border-slate-700 text-slate-300 font-medium";
      case "IN_REVIEW":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold animate-pulse";
      case "APPROVED":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "REJECTED":
        return "bg-rose-950/80 border-rose-600 text-rose-300 font-bold";
      case "DEPLOYED":
        return "bg-purple-950/80 border-purple-600 text-purple-300 font-bold";
      case "CANCELLED":
      default:
        return "bg-slate-900 border-slate-800 text-slate-500";
    }
  };


export const getArchitectureRiskBadge = (risk?: string) => {
    switch (risk) {
      case "LOW":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "MEDIUM":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "HIGH":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "CRITICAL":
      default:
        return "bg-red-950/90 border-red-600 text-red-300 font-black animate-pulse";
    }
  };


export const getCompatibilityStatusBadge = (status?: string) => {
    switch (status) {
      case "BACKWARD_COMPATIBLE":
        return "bg-emerald-950/90 border-emerald-500 text-emerald-300 font-bold shadow-lg shadow-emerald-500/10";
      case "NON_BREAKING":
        return "bg-teal-950/80 border-teal-600 text-teal-300 font-bold";
      case "BREAKING":
        return "bg-red-950/90 border-red-600 text-red-300 font-black animate-pulse";
      case "UNKNOWN":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getDriftStatusBadge = (status?: string) => {
    switch (status) {
      case "IN_SYNC":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "DRIFT_DETECTED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold animate-pulse";
      case "CRITICAL_DRIFT":
        return "bg-red-950/90 border-red-600 text-red-300 font-black animate-pulse";
      case "OVERRIDDEN":
      default:
        return "bg-purple-950/80 border-purple-600 text-purple-300 font-medium";
    }
  };


export const getFeatureFlagStatusBadge = (status?: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-emerald-950/80 border-emerald-600 text-emerald-300 font-bold";
      case "ROLLOUT":
        return "bg-cyan-950/80 border-cyan-600 text-cyan-300 font-bold animate-pulse";
      case "PAUSED":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-bold";
      case "ROLLED_BACK":
        return "bg-orange-950/80 border-orange-600 text-orange-300 font-bold";
      case "RETIRED":
        return "bg-slate-900 border-slate-800 text-slate-500";
      case "CREATED":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };


export const getReleaseStageBadge = (stage?: string) => {
    switch (stage) {
      case "PRODUCTION":
        return "bg-purple-950/90 border-purple-500 text-purple-300 font-black shadow-lg shadow-purple-500/20";
      case "CANARY":
        return "bg-cyan-950/80 border-cyan-500 text-cyan-300 font-bold animate-pulse";
      case "STAGING":
        return "bg-blue-950/80 border-blue-600 text-blue-300 font-bold";
      case "TESTING":
        return "bg-amber-950/80 border-amber-600 text-amber-300 font-semibold";
      case "ROLLED_BACK":
        return "bg-red-950/80 border-red-600 text-red-300 font-bold";
      case "DRAFT":
      default:
        return "bg-slate-900 border-slate-700 text-slate-400";
    }
  };

export const formatPct = (val: number | null) =>
  val !== null ? `${(val * 100).toFixed(1)}%` : "N/A";

export const formatNum = (val: number | null, decimals = 2) =>
  val !== null ? val.toFixed(decimals) : "N/A";

export const formatDelta = (val: number | null, isPct = true) => {
  if (val === null) return "—";
  const prefix = val > 0 ? "+" : "";
  return isPct ? `${prefix}${(val * 100).toFixed(1)}%` : `${prefix}${val.toFixed(3)}`;
};
