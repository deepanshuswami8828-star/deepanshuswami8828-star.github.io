"use client";

import React from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#07090e] text-slate-100 flex items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4 shadow-2xl">
          <div className="w-12 h-12 bg-rose-950/60 border border-rose-800 text-rose-400 rounded-full flex items-center justify-center mx-auto text-xl font-bold">
            ⚡
          </div>
          <h2 className="text-xl font-bold text-white">Application Error</h2>
          <p className="text-slate-400 text-sm leading-relaxed">
            {error?.message || "An unhandled error occurred. Please try reloading."}
          </p>
          <button
            onClick={() => reset()}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-sm transition-all"
          >
            Try Again
          </button>
        </div>
      </body>
    </html>
  );
}
