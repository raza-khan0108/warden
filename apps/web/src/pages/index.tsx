import React from 'react';
import { GitHubSettings } from '@/components/GitHubSettings';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Warden</h1>
        <GitHubSettings />
      </div>
    </main>
  );
}
