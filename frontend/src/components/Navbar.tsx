"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getStoredSession, loginAs, UserRole, UserSession } from "../lib/auth";

export default function Navbar() {
  const pathname = usePathname();
  const [session, setSession] = useState<UserSession>(getStoredSession);

  const handleRoleChange = async (role: UserRole) => {
    try {
      const updated = await loginAs(`user_${role}`, role);
      setSession(updated);
      window.location.reload(); // Refresh data with updated RBAC token
    } catch (err) {
      console.error("Failed to switch role:", err);
    }
  };

  const navItems = [
    { label: "Overview", href: "/" },
    { label: "Recovery Cases", href: "/cases" },
    { label: "Human Review", href: "/review" },
    { label: "Intelligence", href: "/intelligence" },
    { label: "Audit Trail", href: "/audit" },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-indigo-500/20">
              <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-slate-950">
                <span className="text-lg font-black bg-gradient-to-r from-indigo-400 to-cyan-300 bg-clip-text text-transparent">
                  R
                </span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                Recover<span className="text-indigo-400">IQ</span>
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 -mt-1">
                Autonomous Revenue Agent
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/" && pathname?.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {/* RBAC Role Switcher */}
          {session && (
            <div className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs">
              <span className="text-[10px] uppercase font-bold text-slate-400">
                Role:
              </span>
              <select
                value={session.role}
                onChange={(e) => handleRoleChange(e.target.value as UserRole)}
                className="bg-transparent text-xs font-semibold text-indigo-400 focus:outline-none cursor-pointer"
              >
                <option value="operator" className="bg-slate-950 text-slate-200">
                  Operator
                </option>
                <option value="viewer" className="bg-slate-950 text-slate-200">
                  Viewer
                </option>
                <option value="admin" className="bg-slate-950 text-slate-200">
                  Admin
                </option>
              </select>
            </div>
          )}

          <div className="flex items-center gap-2 rounded-full bg-emerald-950/60 border border-emerald-800/40 px-3 py-1 text-xs font-medium text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span>Policy Engine Active</span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs font-medium text-slate-400">
            <svg
              className="w-3.5 h-3.5 text-cyan-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <span>Zero-PII</span>
          </div>
        </div>
      </div>
    </header>
  );
}
