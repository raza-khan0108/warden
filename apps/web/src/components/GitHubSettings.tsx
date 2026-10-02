"use client";

import { useEffect, useState } from "react";
import { getGitHubInstallUrl, getIntegration } from "@/lib/api";

interface GitHubSettingsProps {
  orgId: number;
  token: string;
}

export function GitHubSettings({ orgId, token }: GitHubSettingsProps) {
  const [installUrl, setInstallUrl] = useState<string>("");
  const [installed, setInstalled] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError("");

        // Check if GitHub app is already installed
        try {
          await getIntegration(orgId, "github_app", token);
          setInstalled(true);
        } catch {
          setInstalled(false);
        }

        // Get install URL
        const url = await getGitHubInstallUrl();
        const urlWithOrgId = `${url}&org_id=${orgId}`;
        setInstallUrl(urlWithOrgId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [orgId, token]);

  if (loading) {
    return <div className="p-4">Loading GitHub settings...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-600">Error: {error}</div>;
  }

  return (
    <div className="p-6 border border-gray-300 rounded">
      <h2 className="text-2xl font-bold mb-4">GitHub App</h2>

      {installed ? (
        <div className="mb-4 p-3 bg-green-100 border border-green-400 rounded">
          ✓ GitHub App is installed for this organization
        </div>
      ) : (
        <div className="mb-4 p-3 bg-yellow-100 border border-yellow-400 rounded">
          GitHub App is not yet installed
        </div>
      )}

      <p className="mb-4 text-gray-700">
        The GitHub App gives Warden permission to access your repositories, issues, and PRs.
      </p>

      {installUrl && (
        <a
          href={installUrl}
          className="inline-block px-4 py-2 bg-gray-800 text-white rounded hover:bg-gray-900"
        >
          {installed ? "Reinstall GitHub App" : "Install GitHub App"}
        </a>
      )}
    </div>
  );
}
