"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface HeaderProps {
  publicId?: string;
  pdfUrl?: string;
}

export default function Header({ publicId, pdfUrl }: HeaderProps) {
  const pathname = usePathname();
  const [copied, setCopied] = useState(false);

  const handleShare = () => {
    if (!publicId) return;
    const shareUrl = `${window.location.origin}/r/${publicId}`;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const navItems = [
    { label: "Backtest", href: "/" },
    { label: "History", href: "/history" },
    { label: "Compare", href: "/compare" },
  ];

  return (
    <header className="max-w-7xl mx-auto border-b border-slate-800 pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-6">
        <div>
          <Link href="/" className="group">
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
              BacktestLab
            </h1>
          </Link>
          <p className="text-slate-400 text-sm mt-0.5">
            Indian (NSE) Markets Backtesting Platform
          </p>
        </div>

        <nav className="flex items-center space-x-1 bg-slate-900/80 p-1 rounded-lg border border-slate-800">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-4 py-1.5 rounded-md text-sm font-semibold transition-all ${
                  isActive
                    ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center space-x-3 w-full md:w-auto">
        {publicId && (
          <button
            onClick={handleShare}
            className="flex-1 md:flex-initial flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-sm px-4 py-2.5 rounded-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            {copied ? (
              <>
                <svg className="h-4 w-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-emerald-400 font-bold">Link Copied!</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 100-5.999 3 3 0 000 5.999zm0 11.998a3 3 0 100-5.999 3 3 0 000 5.999z" />
                </svg>
                <span>Share</span>
              </>
            )}
          </button>
        )}

        {pdfUrl && (
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 md:flex-initial flex items-center justify-center space-x-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm px-4 py-2.5 rounded-lg shadow-lg hover:shadow-cyan-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
              <path d="M13 8V2H7v6H2l8 8 8-8h-5zM0 18h20v2H0v-2z" />
            </svg>
            <span>PDF Report</span>
          </a>
        )}
      </div>
    </header>
  );
}
